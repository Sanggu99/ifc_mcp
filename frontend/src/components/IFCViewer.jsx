import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import * as WebIFC from 'web-ifc';
import { getFileUrl, getDXFView } from '../utils/api';

/**
 * IFC 3D Viewer — web-ifc를 직접 사용하여 IFC 파일의 지오메트리를
 * Three.js 메쉬로 변환하고 렌더링합니다.
 * 
 * @thatopen/components의 IfcLoader 대신 web-ifc IfcAPI를 직접 사용하여
 * WASM 경로 문제를 회피하고 안정적인 렌더링을 보장합니다.
 */
export default function IFCViewer({ activeFile, refreshTrigger, onSelectElement, dxfPlane }) {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const animFrameRef = useRef(null);
  const ifcApiRef = useRef(null);
  const modelGroupRef = useRef(null);
  const highlightMeshRef = useRef(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  // DXF 레이어 선택 상태
  const [selectedLayers, setSelectedLayers] = useState([]);
  // DXF 레이어 선택 핸들러
  const handleLayerToggle = (layer) => {
    setSelectedLayers((prev) =>
      prev.includes(layer)
        ? prev.filter((l) => l !== layer)
        : [...prev, layer]
    );
  };

  // ── Section Cut State ────────────────────────────────────────────
  const [sectionEnabled, setSectionEnabled] = useState(false);
  const [sectionAxis, setSectionAxis]   = useState('y');   // 'x' | 'y' | 'z'
  const [sectionValue, setSectionValue] = useState(50);    // 0-100 %
  const modelBoundsRef = useRef(null);  // { min, max, size, center }
  const clippingPlaneRef = useRef(new THREE.Plane(new THREE.Vector3(0, -1, 0), 0));

  // ── Initialize Three.js Scene ──────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e1a);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 5000);
    camera.position.set(20, 15, 20);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    renderer.localClippingEnabled = true;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controls.minDistance = 1;
    controls.maxDistance = 500;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(30, 50, 30);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 200;
    dirLight.shadow.camera.left = -50;
    dirLight.shadow.camera.right = 50;
    dirLight.shadow.camera.top = 50;
    dirLight.shadow.camera.bottom = -50;
    scene.add(dirLight);

    const hemiLight = new THREE.HemisphereLight(0x87ceeb, 0x362d5e, 0.4);
    scene.add(hemiLight);

    // Grid
    const gridHelper = new THREE.GridHelper(100, 100, 0x1a2744, 0x111827);
    gridHelper.position.y = -0.01;
    scene.add(gridHelper);

    // Axes helper (subtle)
    const axesHelper = new THREE.AxesHelper(3);
    axesHelper.material.opacity = 0.4;
    axesHelper.material.transparent = true;
    scene.add(axesHelper);

    // Animation loop
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Initialize web-ifc API
    const initWebIfc = async () => {
      try {
        const ifcApi = new WebIFC.IfcAPI();
        ifcApi.SetWasmPath('/');  // WASM is in public/ folder
        await ifcApi.Init();
        ifcApiRef.current = ifcApi;
        console.log('web-ifc initialized successfully');
      } catch (err) {
        console.error('web-ifc init failed:', err);
      }
    };
    initWebIfc();

    // Setup Raycaster for Selection
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let isDragging = false;
    let mouseDownPos = { x: 0, y: 0 };

    const onPointerDown = (event) => {
      isDragging = false;
      mouseDownPos = { x: event.clientX, y: event.clientY };
    };

    const onPointerMove = (event) => {
      if (Math.abs(event.clientX - mouseDownPos.x) > 3 || Math.abs(event.clientY - mouseDownPos.y) > 3) {
        isDragging = true;
      }
    };

    const onMouseClick = (event) => {
      if (isDragging || !modelGroupRef.current) return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      
      // Check for intersections with model
      const intersects = raycaster.intersectObjects(modelGroupRef.current.children, false);
      
      // Also check for intersection with grid/ground for placement
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
      const groundPoint = new THREE.Vector3();
      raycaster.ray.intersectPlane(plane, groundPoint);

      if (intersects.length > 0) {
        const object = intersects[0].object;
        const expressID = object.userData.expressID;
        const ifcType = object.userData.ifcType;
        const point = intersects[0].point;

        // Apply Highlight
        if (highlightMeshRef.current && highlightMeshRef.current !== object) {
          highlightMeshRef.current.material.emissive.setHex(0x000000);
        }
        object.material.emissive.setHex(0x2ecc71); // Green selection
        highlightMeshRef.current = object;

        // Calculate size for dashboard/modeling panel
        const box = new THREE.Box3().setFromObject(object);
        const size = box.getSize(new THREE.Vector3());
        const dimensions = {
          x: parseFloat(size.x.toFixed(2)),
          y: parseFloat(size.y.toFixed(2)),
          z: parseFloat(size.z.toFixed(2))
        };

        setSelectedId(expressID);
        if (onSelectElement) {
          onSelectElement({ 
            expressID, 
            ifcType, 
            meshId: object.id,
            dimensions,
            point: { x: point.x, y: point.y, z: point.z } 
          });
        }
      } else {
        // Clear selection
        if (highlightMeshRef.current) {
          highlightMeshRef.current.material.emissive.setHex(0x000000);
          highlightMeshRef.current = null;
        }
        setSelectedId(null);
        if (onSelectElement) {
          // If clicked on ground, still pass the point for placement
          onSelectElement({ 
            point: { x: groundPoint.x, y: groundPoint.y, z: groundPoint.z },
            isGround: true 
          });
        }
      }
    };

    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('click', onMouseClick);

    // Cleanup
    return () => {
      cancelAnimationFrame(animFrameRef.current);
      resizeObserver.disconnect();
      controls.dispose();
      
      if (renderer.domElement) {
        renderer.domElement.removeEventListener('pointerdown', onPointerDown);
        renderer.domElement.removeEventListener('pointermove', onPointerMove);
        renderer.domElement.removeEventListener('click', onMouseClick);
      }

      renderer.dispose();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      if (ifcApiRef.current) {
        ifcApiRef.current = null;
      }
    };
  }, []);

  // ── Color palette for IFC types ────────────────────────────────────
  const getColorForType = useCallback((ifcType) => {
    const colors = {
      IFCWALL: 0xe8dcc8,
      IFCWALLSTANDARDCASE: 0xe8dcc8,
      IFCSLAB: 0xc4c4c4,
      IFCROOF: 0x8b6b4a,
      IFCCOLUMN: 0xd4c5a9,
      IFCBEAM: 0xc8b896,
      IFCDOOR: 0x7a5c3a,
      IFCWINDOW: 0x87ceeb,
      IFCSTAIR: 0xbfb5a0,
      IFCSTAIRFLIGHT: 0xbfb5a0,
      IFCRAILING: 0x808080,
      IFCPLATE: 0xa0a0a0,
      IFCMEMBER: 0x909090,
      IFCCURTAINWALL: 0x6bb3d9,
      IFCFURNISHINGELEMENT: 0x8b7355,
      IFCFLOWSEGMENT: 0x4a90d9,
      IFCFLOWTERMINAL: 0x4a90d9,
      IFCSPACE: 0x4466aa,
      IFCOPENINGELEMENT: 0x000000,
      IFCBUILDINGSTOREY: 0x000000,
    };
    const upper = (ifcType || '').toUpperCase();
    return colors[upper] ?? 0xc0b8a8;
  }, []);

  // ── Load File (IFC or DXF) ─────────────────────────────────────────
  const loadFile = useCallback(async () => {
    if (!activeFile) return;
    const isIFC = activeFile.toLowerCase().endsWith('.ifc');
    const isDXF = activeFile.toLowerCase().endsWith('.dxf');
    if (!isIFC && !isDXF) return;

    if (isIFC && (!sceneRef.current || !ifcApiRef.current)) {
      // Retry after web-ifc init
      setTimeout(() => loadFile(), 500);
      return;
    }

    setLoading(true);
    setError(null);
    setModelInfo(null);

    const scene = sceneRef.current;
    const ifcApi = ifcApiRef.current;

    // Remove previous model
    if (modelGroupRef.current) {
      if (highlightMeshRef.current) highlightMeshRef.current = null;
      if (onSelectElement) onSelectElement(null);
      setSelectedId(null);

      scene.remove(modelGroupRef.current);
      modelGroupRef.current.traverse((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) {
            child.material.forEach(m => m.dispose());
          } else {
            child.material.dispose();
          }
        }
      });
      modelGroupRef.current = null;
    }

    try {
      if (isDXF) {
        // Fetch DXF Data
        const viewData = await getDXFView(activeFile);
        const modelGroup = new THREE.Group();
        modelGroup.name = activeFile;
        modelGroup.userData.isDXF = true;

        // 항상 XY 평면(바닥) 기준으로 렌더링
        const transformPoint = (p) => {
          let [x, y, z] = p;
          return new THREE.Vector3(x, y, z);
        };

        // --- 레이어별 그룹화 및 색상 적용 ---
        // DXF 데이터는 lines, polylines, 각 엔티티에 layer/color 정보가 포함되어야 함
        // { lines: [{start, end, layer, color}], polylines: [{points, is_closed, layer, color}], layers: ["WALL", ...] }
        const layerGroups = {};
        const layerColors = {};
        // lines
        if (viewData.lines && viewData.lines.length > 0) {
          viewData.lines.forEach(l => {
            const layer = l.layer || 'default';
            if (!layerGroups[layer]) {
              layerGroups[layer] = new THREE.Group();
              layerGroups[layer].name = `layer:${layer}`;
            }
            // l.color: '#rrggbb' 또는 undefined
            let color = 0x888888;
            if (l.color && typeof l.color === 'string' && l.color.startsWith('#')) {
              color = Number('0x' + l.color.slice(1));
            }
            layerColors[layer] = color;
            const lineMat = new THREE.LineBasicMaterial({ color });
            const lineGeo = new THREE.BufferGeometry();
            lineGeo.setFromPoints([transformPoint(l.start), transformPoint(l.end)]);
            const line = new THREE.Line(lineGeo, lineMat);
            layerGroups[layer].add(line);
          });
        }
        // polylines
        if (viewData.polylines) {
          viewData.polylines.forEach(poly => {
            const layer = poly.layer || 'default';
            if (!layerGroups[layer]) {
              layerGroups[layer] = new THREE.Group();
              layerGroups[layer].name = `layer:${layer}`;
            }
            let color = 0xaaaaaa;
            if (poly.color && typeof poly.color === 'string' && poly.color.startsWith('#')) {
              color = Number('0x' + poly.color.slice(1));
            }
            layerColors[layer] = color;
            const polyMat = new THREE.LineBasicMaterial({ color });
            const polyGeo = new THREE.BufferGeometry();
            const pts = poly.points.map(p => transformPoint(p));
            if (poly.is_closed) pts.push(pts[0].clone());
            polyGeo.setFromPoints(pts);
            const polyLine = new THREE.Line(polyGeo, polyMat);
            layerGroups[layer].add(polyLine);
          });
        }
        // 그룹을 모델에 추가
        Object.values(layerGroups).forEach(g => modelGroup.add(g));

        // Save layers to model info
        const layers = viewData.layers || Object.keys(layerGroups);

        scene.add(modelGroup);
        modelGroupRef.current = modelGroup;

        // Fit camera to model
        const box = new THREE.Box3().setFromObject(modelGroup);
        if (!box.isEmpty()) {
          const center = box.getCenter(new THREE.Vector3());
          const size = box.getSize(new THREE.Vector3());
          const maxDim = Math.max(size.x, size.y, size.z);
          const dist = maxDim * 1.8;

          if (cameraRef.current && controlsRef.current) {
            cameraRef.current.position.set(center.x, center.y + dist * 0.8, center.z + dist * 0.1);
            controlsRef.current.target.copy(center);
            controlsRef.current.update();
            cameraRef.current.far = Math.max(5000, maxDim * 10);
            cameraRef.current.updateProjectionMatrix();
          }

          modelBoundsRef.current = { min: box.min.clone(), max: box.max.clone(), size: size.clone(), center: center.clone() };

          setModelInfo({
            name: activeFile,
            meshCount: Object.values(layerGroups).reduce((acc, g) => acc + g.children.length, 0),
            dimensions: { x: size.x.toFixed(2), y: size.y.toFixed(2), z: size.z.toFixed(2) },
            layers: layers,
            layerColors: layerColors
          });
        }

        setLoading(false);
        return;
      }

      // Fetch IFC file
      const url = getFileUrl(activeFile);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`파일 다운로드 실패 (${response.status})`);

      const buffer = await response.arrayBuffer();
      const data = new Uint8Array(buffer);

      // Open model in web-ifc
      const modelID = ifcApi.OpenModel(data, {
        COORDINATE_TO_ORIGIN: true,
        USE_FAST_BOOLS: true,
      });

      console.log(`IFC model opened: ID=${modelID}, file=${activeFile}`);

      // Create Three.js group for the model
      const modelGroup = new THREE.Group();
      modelGroup.name = activeFile;

      // Stream all meshes
      ifcApi.StreamAllMeshes(modelID, (mesh) => {
        const placedGeometries = mesh.geometries;

        for (let i = 0; i < placedGeometries.size(); i++) {
          const placedGeometry = placedGeometries.get(i);
          const ifcGeometry = ifcApi.GetGeometry(modelID, placedGeometry.geometryExpressID);

          // Index data
          const indexData = ifcApi.GetIndexArray(
            ifcGeometry.GetIndexData(),
            ifcGeometry.GetIndexDataSize()
          );
          // Vertex data (x, y, z, nx, ny, nz per vertex)
          const vertexData = ifcApi.GetVertexArray(
            ifcGeometry.GetVertexData(),
            ifcGeometry.GetVertexDataSize()
          );

          if (indexData.length === 0 || vertexData.length === 0) {
            ifcGeometry.delete();
            continue;
          }

          // Build Three.js BufferGeometry
          const geometry = new THREE.BufferGeometry();

          // Separate positions and normals from interleaved vertex data
          const vertexCount = vertexData.length / 6;
          const positions = new Float32Array(vertexCount * 3);
          const normals = new Float32Array(vertexCount * 3);

          for (let v = 0; v < vertexCount; v++) {
            positions[v * 3 + 0] = vertexData[v * 6 + 0];
            positions[v * 3 + 1] = vertexData[v * 6 + 1];
            positions[v * 3 + 2] = vertexData[v * 6 + 2];
            normals[v * 3 + 0] = vertexData[v * 6 + 3];
            normals[v * 3 + 1] = vertexData[v * 6 + 4];
            normals[v * 3 + 2] = vertexData[v * 6 + 5];
          }

          geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
          geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
          geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(indexData), 1));

          // Get IFC type for color
          let ifcType = '';
          try {
            const typeId = ifcApi.GetLineIDsWithType(modelID, mesh.expressID)
            ifcType = ifcApi.GetLine(modelID, mesh.expressID)?.constructor?.name || '';
          } catch (e) {
            // Fallback: just use default color
          }

          // Determine color from the geometry's color in the IFC
          const color = new THREE.Color(
            placedGeometry.color.x,
            placedGeometry.color.y,
            placedGeometry.color.z
          );
          const opacity = placedGeometry.color.w;

          // Skip fully transparent geometries (like IfcSpace, IfcOpeningElement)
          if (opacity < 0.01) {
            ifcGeometry.delete();
            continue;
          }

          // Material
          const material = new THREE.MeshPhysicalMaterial({
            color: color,
            transparent: opacity < 0.99,
            opacity: opacity,
            side: THREE.DoubleSide,
            roughness: 0.65,
            metalness: 0.05,
            clearcoat: 0.1,
            depthWrite: opacity >= 0.99,
          });

          const mesh3D = new THREE.Mesh(geometry, material);
          mesh3D.receiveShadow = true;
          mesh3D.castShadow = true;
          
          // Store original express ID and type for selection and AI context
          mesh3D.userData = {
            expressID: mesh.expressID,
            ifcType: ifcType
          };

          // Apply transformation matrix
          const flatMatrix = placedGeometry.flatTransformation;
          const matrix = new THREE.Matrix4();
          matrix.set(
            flatMatrix[0], flatMatrix[4], flatMatrix[8], flatMatrix[12],
            flatMatrix[1], flatMatrix[5], flatMatrix[9], flatMatrix[13],
            flatMatrix[2], flatMatrix[6], flatMatrix[10], flatMatrix[14],
            flatMatrix[3], flatMatrix[7], flatMatrix[11], flatMatrix[15]
          );
          mesh3D.applyMatrix4(matrix);

          modelGroup.add(mesh3D);
          ifcGeometry.delete();
        }
      });

      // Close model to free WASM memory
      ifcApi.CloseModel(modelID);

      // Add to scene
      scene.add(modelGroup);
      modelGroupRef.current = modelGroup;

      // Fit camera to model
      const box = new THREE.Box3().setFromObject(modelGroup);
      if (!box.isEmpty()) {
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const dist = maxDim * 1.8;

        if (cameraRef.current && controlsRef.current) {
          cameraRef.current.position.set(
            center.x + dist * 0.7,
            center.y + dist * 0.5,
            center.z + dist * 0.7
          );
          controlsRef.current.target.copy(center);
          controlsRef.current.update();

          // Adjust camera far plane for large models
          cameraRef.current.far = Math.max(5000, maxDim * 10);
          cameraRef.current.updateProjectionMatrix();
        }

        // Store bounds for section cut
        modelBoundsRef.current = {
          min: box.min.clone(),
          max: box.max.clone(),
          size: size.clone(),
          center: center.clone(),
        };

        setModelInfo({
          name: activeFile,
          meshCount: modelGroup.children.length,
          dimensions: {
            x: size.x.toFixed(2),
            y: size.y.toFixed(2),
            z: size.z.toFixed(2),
          },
        });

        console.log(`IFC loaded: ${modelGroup.children.length} meshes, size=${size.x.toFixed(1)}x${size.y.toFixed(1)}x${size.z.toFixed(1)}`);
      } else {
        setError('모델에 표시 가능한 지오메트리가 없습니다.');
      }

      setLoading(false);
    } catch (err) {
      console.error('IFC load error:', err);
      setLoading(false);
    }
  }, [activeFile, getColorForType, dxfPlane]);

  // DXF 파일이 바뀌면 선택 레이어 초기화
  useEffect(() => {
    setSelectedLayers([]);
  }, [activeFile]);

  useEffect(() => {
    loadFile();
  }, [activeFile, refreshTrigger, loadFile, dxfPlane]);
  // DXF 레이어 가시성 동기화
  useEffect(() => {
    if (!modelInfo || !modelGroupRef.current || !modelInfo.layers) return;
    // DXF가 아닐 때는 무시
    if (!modelGroupRef.current.userData.isDXF) return;
    // 선택이 없으면 전체 표시
    const showAll = selectedLayers.length === 0;
    modelInfo.layers.forEach((layer) => {
      const group = modelGroupRef.current.getObjectByName(`layer:${layer}`);
      if (group) group.visible = showAll || selectedLayers.includes(layer);
    });
  }, [selectedLayers, modelInfo]);

  // ── Section Cut Effect ────────────────────────────────────────────
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;

    if (!sectionEnabled) {
      renderer.clippingPlanes = [];
      return;
    }

    const bounds = modelBoundsRef.current;
    if (!bounds) return;

    // Map sectionValue (0-100%) to world coordinate along chosen axis
    const { min, max } = bounds;
    let worldPos;
    let normal;
    if (sectionAxis === 'x') {
      worldPos = min.x + (max.x - min.x) * (sectionValue / 100);
      normal = new THREE.Vector3(-1, 0, 0);
    } else if (sectionAxis === 'y') {
      worldPos = min.y + (max.y - min.y) * (sectionValue / 100);
      normal = new THREE.Vector3(0, -1, 0);
    } else {
      worldPos = min.z + (max.z - min.z) * (sectionValue / 100);
      normal = new THREE.Vector3(0, 0, -1);
    }

    // THREE.Plane: normal·x + constant = 0  →  constant = worldPos
    clippingPlaneRef.current.normal.copy(normal);
    clippingPlaneRef.current.constant = worldPos;
    renderer.clippingPlanes = [clippingPlaneRef.current];
  }, [sectionEnabled, sectionAxis, sectionValue]);

  return (
    <div className="viewer-container">
      <div ref={containerRef} className="w-full h-full" id="ifc-viewer-canvas" />

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface-950/60 backdrop-blur-sm z-10">
          <div className="flex flex-col items-center gap-3 animate-fade-in">
            <div className="spinner"></div>
            <p className="text-sm text-surface-300">IFC 모델 로딩 중...</p>
            <p className="text-xs text-surface-500">web-ifc로 지오메트리 파싱 중</p>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {error && (
        <div className="absolute bottom-4 left-4 right-4 z-10">
          <div className="glass-panel-light p-3 text-xs text-warn-400 animate-slide-up">
            ⚠️ {error}
          </div>
        </div>
      )}

      {/* Model info overlay + DXF 레이어 선택 UI */}
      {modelInfo && !loading && (
        <div className="absolute top-3 left-3 z-10 animate-fade-in flex flex-col gap-2">
          <div className="glass-panel-light px-3 py-2">
            <p className="text-xs font-medium text-surface-200 truncate max-w-[220px]">
              📐 {modelInfo.name}
            </p>
            <p className="text-[10px] text-surface-400 mt-0.5 font-mono">
              {modelInfo.dimensions.x} × {modelInfo.dimensions.y} × {modelInfo.dimensions.z} m
            </p>
            <p className="text-[10px] text-surface-500 font-mono">
              🧱 {modelInfo.meshCount} meshes
            </p>
          </div>

          {/* DXF 레이어 선택 UI */}
          {modelInfo.layers && modelInfo.layers.length > 0 && modelGroupRef.current?.userData?.isDXF && (
            <div className="glass-panel-light px-3 py-2 mt-1">
              <p className="text-[10px] text-blue-400 font-bold mb-1">DXF 레이어 선택 (중복 가능)</p>
              <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                {modelInfo.layers.map((layer) => (
                  <label key={layer} className="flex items-center gap-2 text-xs cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={selectedLayers.length === 0 || selectedLayers.includes(layer)}
                      onChange={() => handleLayerToggle(layer)}
                      className="accent-blue-500"
                    />
                    <span style={{ color: modelInfo.layerColors?.[layer] ? `#${modelInfo.layerColors[layer].toString(16).padStart(6, '0')}` : undefined }}>
                      {layer}
                    </span>
                  </label>
                ))}
              </div>
              <p className="text-[9px] text-surface-500 mt-1">※ 아무것도 선택하지 않으면 전체 표시</p>
            </div>
          )}

          {/* Selection Object Info Bubble */}
          {selectedId && (
            <div className="glass-panel-light border-green-500/30 bg-green-500/10 px-3 py-2 animate-slide-up">
              <p className="text-[10px] text-green-400/80 uppercase font-bold tracking-wider mb-1">
                Selected Element
              </p>
              <div className="flex flex-col gap-0.5">
                <p className="text-xs font-bold text-surface-100 uppercase">
                  {highlightMeshRef.current?.userData?.ifcType?.replace('IFC', '') || 'Element'}
                </p>
                <p className="text-[11px] font-mono text-green-300">
                  {(() => {
                    if (!highlightMeshRef.current) return '';
                    const box = new THREE.Box3().setFromObject(highlightMeshRef.current);
                    const size = box.getSize(new THREE.Vector3());
                    return `${size.x.toFixed(2)}m × ${size.y.toFixed(2)}m × ${size.z.toFixed(2)}m`;
                  })()}
                </p>
                <p className="text-[9px] font-mono text-surface-400">
                  ID: #{selectedId}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Section Cut Controls ──────────────────────────────── */}
      {modelInfo && !loading && (
        <div className="absolute top-3 right-3 z-20 flex flex-col gap-2 animate-fade-in">
          {/* Toggle button */}
          <button
            onClick={() => setSectionEnabled(v => !v)}
            className={`glass-panel-light px-3 py-1.5 text-xs font-semibold transition-colors ${
              sectionEnabled
                ? 'text-blue-300 border-blue-500/50 bg-blue-500/20'
                : 'text-surface-400 hover:text-surface-200'
            }`}
            title="단면 자르기 ON/OFF"
          >
            ✂️ 단면 {sectionEnabled ? 'ON' : 'OFF'}
          </button>

          {/* Axis + Slider — only when enabled */}
          {sectionEnabled && (
            <div className="glass-panel-light px-3 py-2.5 flex flex-col gap-2 min-w-[160px]">
              {/* Axis selector */}
              <div className="flex gap-1">
                {['x', 'y', 'z'].map(ax => (
                  <button
                    key={ax}
                    onClick={() => setSectionAxis(ax)}
                    className={`flex-1 py-0.5 text-[11px] font-bold rounded transition-colors ${
                      sectionAxis === ax
                        ? 'bg-blue-500/40 text-blue-200'
                        : 'text-surface-400 hover:text-surface-200'
                    }`}
                  >
                    {ax.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Slider */}
              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-[10px] text-surface-500 font-mono">
                  <span>0%</span>
                  <span className="text-blue-300">{sectionValue}%</span>
                  <span>100%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={sectionValue}
                  onChange={e => setSectionValue(Number(e.target.value))}
                  className="w-full accent-blue-400 cursor-pointer"
                />
              </div>

              {/* World coordinate readout */}
              {modelBoundsRef.current && (
                <p className="text-[9px] text-surface-500 font-mono text-center">
                  {(() => {
                    const { min, max } = modelBoundsRef.current;
                    const pos = sectionAxis === 'x'
                      ? min.x + (max.x - min.x) * (sectionValue / 100)
                      : sectionAxis === 'y'
                        ? min.y + (max.y - min.y) * (sectionValue / 100)
                        : min.z + (max.z - min.z) * (sectionValue / 100);
                    return `${sectionAxis.toUpperCase()} = ${pos.toFixed(2)} m`;
                  })()}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Controls hint */}
      {modelInfo && !loading && (
        <div className="absolute bottom-3 right-3 z-10">
          <div className="glass-panel-light px-2.5 py-1.5 text-[10px] text-surface-500">
            🖱️ 회전 · 우클릭 이동 · 스크롤 줌
          </div>
        </div>
      )}

      {/* No file placeholder */}
      {!activeFile && !loading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-5">
          <div className="text-center animate-fade-in">
            <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-surface-800/40 flex items-center justify-center border border-white/5">
              <svg className="w-10 h-10 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
              </svg>
            </div>
            <p className="text-surface-500 text-sm">도면(DXF) 또는 모델(IFC) 파일을 선택하세요</p>
            <p className="text-surface-600 text-xs mt-1">도면은 웹에서 확인 후 바로 모델링이 가능합니다</p>
          </div>
        </div>
      )}
    </div>
  );
}
