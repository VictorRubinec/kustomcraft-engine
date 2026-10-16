import * as THREE from 'three';

/**
 * Cria a geometria e malhas de uma única caneca de cerâmica AAA com arte sublimática e sombra.
 */
function createMugGroup(textures, porcelainMat, shadowTex) {
  const group = new THREE.Group();

  // 1. Corpo Cerâmico da Caneca (Perfil Torneado Suave)
  const pts = [
    new THREE.Vector2(0, -1.0),
    new THREE.Vector2(0.85, -1.0),
    new THREE.Vector2(0.88, -0.96),
    new THREE.Vector2(0.90, 0.96),
    new THREE.Vector2(0.88, 1.0),
    new THREE.Vector2(0.82, 1.0),
    new THREE.Vector2(0.80, 0.96),
    new THREE.Vector2(0.78, -0.86),
    new THREE.Vector2(0, -0.86)
  ];
  const mugBodyGeo = new THREE.LatheGeometry(pts, 64);
  const mugBody = new THREE.Mesh(mugBodyGeo, porcelainMat);
  group.add(mugBody);

  // 2. Alça Ergonômica D-Shape (alinhada em +Z na folga da estampa)
  class MugHandleCurve extends THREE.Curve {
    getPoint(t) {
      const a = (t - 0.5) * Math.PI * 1.15;
      const z = 0.88 + Math.cos(a) * 0.48;
      const y = Math.sin(a) * 0.65;
      return new THREE.Vector3(0, y, z);
    }
  }
  const handleGeo = new THREE.TubeGeometry(new MugHandleCurve(), 48, 0.11, 24, false);
  const handleMesh = new THREE.Mesh(handleGeo, porcelainMat);
  group.add(handleMesh);

  // 3. Aplicação da Estampa Sublimática Panorâmica (220x95mm)
  if (textures.art) {
    textures.art.colorSpace = THREE.SRGBColorSpace;
    textures.art.generateMipmaps = true;
    textures.art.minFilter = THREE.LinearMipmapLinearFilter;

    // Envolve o corpo cilíndrico deixando o vão da alça em +Z
    // e o centro da arte (U = 0.5) em -Z (oposto à alça)
    const thetaLength = Math.PI * 1.68;
    const thetaStart = Math.PI - 0.5 * thetaLength;
    const wrapGeo = new THREE.CylinderGeometry(0.904, 0.884, 1.82, 64, 1, true, thetaStart, thetaLength);
    const wrapMat = new THREE.MeshPhysicalMaterial({
      map: textures.art,
      roughness: 0.15,
      metalness: 0.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.06,
      side: THREE.DoubleSide
    });
    const wrapMesh = new THREE.Mesh(wrapGeo, wrapMat);
    group.add(wrapMesh);
  }

  // 4. Sombra de Contato Suave
  const shadowGeo = new THREE.PlaneGeometry(2.6, 2.6);
  const shadowMat = new THREE.MeshBasicMaterial({
    map: shadowTex,
    transparent: true,
    opacity: 0.85,
    depthWrite: false
  });
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
  shadowMesh.rotation.x = -Math.PI / 2;
  shadowMesh.position.y = -1.02;
  group.add(shadowMesh);

  return group;
}

export function setupMugScene(scene, camera, config, textures) {
  const angle = config.angle || 'front_left';

  // Iluminação de Estúdio Fotorrealista
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xfff8ee, 2.2);
  keyLight.position.set(3.5, 4.0, 3.5);
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(0xddeeff, 1.8);
  rimLight.position.set(-3.5, 2.5, -3.0);
  scene.add(rimLight);

  const fillLight = new THREE.DirectionalLight(0xffeedd, 0.9);
  fillLight.position.set(0, -2.5, 2.5);
  scene.add(fillLight);

  // Material de Porcelana Branca Resinada AAA
  const porcelainMat = new THREE.MeshPhysicalMaterial({
    color: 0xfdfdfd,
    roughness: 0.12,
    metalness: 0.04,
    clearcoat: 1.0,
    clearcoatRoughness: 0.05,
    reflectivity: 0.9
  });

  // Textura de Sombra de Contato
  const shadowCanvas = document.createElement('canvas');
  shadowCanvas.width = 128;
  shadowCanvas.height = 128;
  const sCtx = shadowCanvas.getContext('2d');
  const grad = sCtx.createRadialGradient(64, 64, 10, 64, 64, 60);
  grad.addColorStop(0, 'rgba(10, 5, 20, 0.45)');
  grad.addColorStop(0.5, 'rgba(10, 5, 20, 0.15)');
  grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
  sCtx.fillStyle = grad;
  sCtx.fillRect(0, 0, 128, 128);
  const shadowTex = new THREE.CanvasTexture(shadowCanvas);

  if (angle === 'panoramic_trio' || config.scene === 'mug_trio') {
    // Configuração de Câmera para o Trio Panorâmico (enquadra os 3 modelos com margens confortáveis)
    camera.position.set(0.0, 1.2, 11.5);
    camera.lookAt(0.0, 0.0, 0.0);

    // Caneca 1 (Esquerda - Face Esquerda visível com Charizard, alça voltada suavemente para lateral/fundo)
    const mugLeft = createMugGroup(textures, porcelainMat, shadowTex);
    mugLeft.position.set(-1.65, 0, -0.25);
    mugLeft.rotation.y = Math.PI + 1.15;
    scene.add(mugLeft);

    // Caneca 2 (Centro - Face Central visível de frente, Y = Math.PI, elevada a z = 0.35 para profundidade)
    const mugCenter = createMugGroup(textures, porcelainMat, shadowTex);
    mugCenter.position.set(0.0, 0, 0.35);
    mugCenter.rotation.y = Math.PI;
    scene.add(mugCenter);

    // Caneca 3 (Direita - Face Direita visível com Studio Kustom e alça em perfil elegante)
    const mugRight = createMugGroup(textures, porcelainMat, shadowTex);
    mugRight.position.set(1.65, 0, -0.25);
    mugRight.rotation.y = Math.PI - 1.15;
    scene.add(mugRight);
  } else {
    // Configuração de Câmera por Ângulo Individual
    if (angle === 'front_left') {
      camera.position.set(2.4, 1.2, 3.8);
    } else if (angle === 'front_right') {
      camera.position.set(-2.4, 1.2, 3.8);
    } else if (angle === 'front_center') {
      camera.position.set(0.0, 0.8, 4.2);
    } else if (angle === 'top_angle') {
      camera.position.set(1.8, 3.2, 3.2);
    } else {
      camera.position.set(2.4, 1.2, 3.8);
    }
    camera.lookAt(0, 0, 0);

    const singleMug = createMugGroup(textures, porcelainMat, shadowTex);
    singleMug.rotation.y = Math.PI - 0.75;
    scene.add(singleMug);
  }
}
