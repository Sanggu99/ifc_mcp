# Step 1: Interactive 3D Selection

**상태**: ✅ Phase 1에서 이미 완료됨  
**완료일**: 2026-04-15  

---

## 구현 내용

`frontend/src/components/IFCViewer.jsx` 내에 Raycast 기반 3D 객체 선택이
Phase 1 개발 중에 함께 구현되었습니다.

### 동작 방식

1. 사용자가 3D 뷰어 캔버스를 클릭
2. `THREE.Raycaster`가 마우스 좌표 → 카메라 → 씬 방향으로 Ray 발사
3. `raycaster.intersectObjects(modelGroupRef.current.children, false)`로 메쉬 충돌 감지
4. 충돌한 메쉬의 `userData.expressID`와 `userData.ifcType` 추출
5. `object.material.emissive.setHex(0x2ecc71)` 초록 하이라이트 적용
6. `onSelectElement({expressID, ifcType, dimensions, point})` 콜백으로 App.jsx에 전달
7. App.jsx → ChatPanel, ModelingPanel에 `selectedElement` props 전달

### 드래그 vs 클릭 구분

```js
let isDragging = false;
const onPointerDown = (e) => { mouseDownPos = { x: e.clientX, y: e.clientY }; };
const onPointerMove = (e) => {
  if (Math.abs(e.clientX - mouseDownPos.x) > 3 ...) isDragging = true;
};
const onMouseClick = (e) => {
  if (isDragging) return; // 드래그면 선택 무시
  ...
};
```

### 지면 클릭 (배치용)

모델 외 빈 공간 클릭 시 `IfcPlane` 교차점 계산:
```js
const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
raycaster.ray.intersectPlane(plane, groundPoint);
onSelectElement({ point: groundPoint, isGround: true });
```
→ `ModelingPanel`의 "Pick on Viewer" 기능에 사용

---

## 연결된 컴포넌트

| 컴포넌트 | 역할 |
|---------|------|
| `IFCViewer.jsx` | Raycast 처리, 하이라이트, 콜백 호출 |
| `App.jsx` | `selectedElement` 상태 관리 |
| `ChatPanel.jsx` | `selectedElement.expressID` → `context_id`로 Gemini에 전달 |
| `ModelingPanel.jsx` | 선택 요소 정보 표시, 이동/삭제 버튼, Pick 좌표 수신 |
