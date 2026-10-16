import * as THREE from 'three';

/**
 * Cena de Pôster Papel Puro Couché 300g Suspenso (sem moldura e sem vidro).
 * Renderiza o papel encorpado com núcleo branco visível no contorno refilado,
 * acabamento fotorrealista de termolaminação Hi-Tac com reflexo diagonal suave
 * e sombra flutuante projetada no fundo.
 */
export function setupPosterScene(scene, camera, config, textures) {
  // Configuração de Câmera Frontal Levemente Angular
  camera.position.set(0.16, 0.06, 3.9);
  camera.lookAt(0, 0, 0);

  // Iluminação de Estúdio Fotorrealista para Papelaria Fina e Acabamento Hi-Tac
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
  scene.add(ambientLight);

  // Luz principal suave do estúdio
  const keyLight = new THREE.DirectionalLight(0xfffaed, 1.8);
  keyLight.position.set(2.8, 3.4, 2.6);
  scene.add(keyLight);

  // Luz diagonal específica para simular o reflexo acetinado da película de termolaminação Hi-Tac
  const hiTacReflectionLight = new THREE.DirectionalLight(0xffffff, 1.2);
  hiTacReflectionLight.position.set(-3.2, 4.2, 2.5);
  scene.add(hiTacReflectionLight);

  // Luz suave de preenchimento inferior
  const fillLight = new THREE.DirectionalLight(0xeef4fc, 0.7);
  fillLight.position.set(-2.0, -2.0, 2.0);
  scene.add(fillLight);

  const group = new THREE.Group();

  const posterW = 1.6;
  const posterH = posterW * (297 / 210); // Proporção A4/A3 padrão ~ 2.26
  const paperThickness = 0.008; // Espessura palpável da chapa de Couché 300g (~0.4mm em escala)

  // 1. Textura da Arte do Pôster com Máxima Fidelidade
  if (textures.art) {
    textures.art.colorSpace = THREE.SRGBColorSpace;
    textures.art.generateMipmaps = true;
    textures.art.minFilter = THREE.LinearMipmapLinearFilter;
  }

  // 2. Núcleo de celulose 100% branco cortado no refile guilhotinado (bordas laterais)
  const edgeMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.92,
    metalness: 0.0,
  });

  // 3. Verso do papel couché fosco
  const backMat = new THREE.MeshStandardMaterial({
    color: 0xfafafa,
    roughness: 0.88,
    metalness: 0.0,
  });

  // 4. Face frontal: Arte Impressa com Película Protetora Hi-Tac (Semi-brilho acetinado com reflexo diagonal)
  const frontArtMat = new THREE.MeshPhysicalMaterial({
    map: textures.art || null,
    color: textures.art ? 0xffffff : 0x2e7d32,
    roughness: 0.20, // Acabamento suave acetinado
    metalness: 0.01,
    clearcoat: 0.70, // Simulação de película Hi-Tac
    clearcoatRoughness: 0.22,
    reflectivity: 0.85,
  });

  // Ordem das faces no Three.js BoxGeometry:
  // 0: +X (borda direita), 1: -X (borda esquerda),
  // 2: +Y (borda superior), 3: -Y (borda inferior),
  // 4: +Z (face frontal com arte), 5: -Z (face traseira / verso)
  const materials = [edgeMat, edgeMat, edgeMat, edgeMat, frontArtMat, backMat];
  const posterGeo = new THREE.BoxGeometry(posterW, posterH, paperThickness);
  const posterMesh = new THREE.Mesh(posterGeo, materials);
  group.add(posterMesh);

  // Inclinação Sutil de Apresentação Flutuante
  group.rotation.set(-0.04, -0.06, 0.015);
  scene.add(group);

  // 4. Sombra Flutuante Suave Projetada no Fundo
  const shadowGeo = new THREE.PlaneGeometry(posterW + 0.6, posterH + 0.6);
  const shadowCanvas = document.createElement('canvas');
  shadowCanvas.width = 128;
  shadowCanvas.height = 128;
  const sCtx = shadowCanvas.getContext('2d');
  const grad = sCtx.createRadialGradient(64, 64, 25, 64, 64, 64);
  grad.addColorStop(0, 'rgba(15, 8, 25, 0.42)');
  grad.addColorStop(0.65, 'rgba(15, 8, 25, 0.12)');
  grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
  sCtx.fillStyle = grad;
  sCtx.fillRect(0, 0, 128, 128);

  const shadowTex = new THREE.CanvasTexture(shadowCanvas);
  const shadowMat = new THREE.MeshBasicMaterial({
    map: shadowTex,
    transparent: true,
    opacity: 0.65,
    depthWrite: false,
  });
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
  shadowMesh.position.set(0.12, -0.14, -0.15);
  scene.add(shadowMesh);
}
