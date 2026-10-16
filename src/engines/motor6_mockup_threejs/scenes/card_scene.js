import * as THREE from 'three';

function createRoundedCardGeometry(width, height, radius, thickness) {
  const shape = new THREE.Shape();
  const x = -width / 2;
  const y = -height / 2;
  shape.moveTo(x + radius, y);
  shape.lineTo(x + width - radius, y);
  shape.quadraticCurveTo(x + width, y, x + width, y + radius);
  shape.lineTo(x + width, y + height - radius);
  shape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  shape.lineTo(x + radius, y + height);
  shape.quadraticCurveTo(x, y + height, x, y + height - radius);
  shape.lineTo(x, y + radius);
  shape.quadraticCurveTo(x, y, x + radius, y);

  const extrudeSettings = {
    depth: thickness,
    bevelEnabled: true,
    bevelSegments: 2,
    steps: 1,
    bevelSize: 0.005,
    bevelThickness: 0.005
  };
  return new THREE.ExtrudeGeometry(shape, extrudeSettings);
}

function createSingleCardMesh(frontTex, backTex, isHolo) {
  const group = new THREE.Group();

  const width = 1.4;
  const height = width * (88.9 / 63.5); // 1.96
  const radius = 0.08;
  const thickness = 0.015;

  // Material do Núcleo do Papel Couché 300g (borda branca fosca)
  const coreGeo = createRoundedCardGeometry(width, height, radius, thickness);
  const coreMat = new THREE.MeshStandardMaterial({
    color: 0xf5f5f5,
    roughness: 0.6,
    metalness: 0.0
  });
  const coreMesh = new THREE.Mesh(coreGeo, coreMat);
  coreMesh.position.z = -thickness / 2;
  group.add(coreMesh);

  // Geometria Plana com Cantos Arredondados para as Faces Frente e Verso
  const faceShape = new THREE.Shape();
  const x = -width / 2;
  const y = -height / 2;
  faceShape.moveTo(x + radius, y);
  faceShape.lineTo(x + width - radius, y);
  faceShape.quadraticCurveTo(x + width, y, x + width, y + radius);
  faceShape.lineTo(x + width, y + height - radius);
  faceShape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  faceShape.lineTo(x + radius, y + height);
  faceShape.quadraticCurveTo(x, y + height, x, y + height - radius);
  faceShape.lineTo(x, y + radius);
  faceShape.quadraticCurveTo(x, y, x + radius, y);

  const faceGeo = new THREE.ShapeGeometry(faceShape, 16);

  // Normalizar UVs da Face para [0, 1]
  const pos = faceGeo.attributes.position;
  const uvs = [];
  for (let i = 0; i < pos.count; i++) {
    const px = pos.getX(i);
    const py = pos.getY(i);
    uvs.push((px - x) / width, (py - y) / height);
  }
  faceGeo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));

  // Material da Frente com Shader de Foil Holográfico
  const frontMat = new THREE.MeshPhysicalMaterial({
    map: frontTex || null,
    color: frontTex ? 0xffffff : 0x2244aa,
    roughness: isHolo ? 0.16 : 0.28,
    metalness: isHolo ? 0.15 : 0.02,
    clearcoat: 1.0,
    clearcoatRoughness: 0.06,
    iridescence: isHolo ? 1.0 : 0.0,
    iridescenceIOR: 1.35,
    iridescenceThicknessRange: [120, 380],
    reflectivity: isHolo ? 0.95 : 0.5
  });

  const frontMesh = new THREE.Mesh(faceGeo, frontMat);
  frontMesh.position.z = thickness / 2 + 0.006;
  group.add(frontMesh);

  // Verso da Carta
  const backMat = new THREE.MeshPhysicalMaterial({
    map: backTex || null,
    color: backTex ? 0xffffff : 0x112244,
    roughness: 0.28,
    metalness: 0.02,
    clearcoat: 0.8,
    clearcoatRoughness: 0.08
  });
  const backMesh = new THREE.Mesh(faceGeo, backMat);
  backMesh.rotation.y = Math.PI;
  backMesh.position.z = -(thickness / 2 + 0.006);
  group.add(backMesh);

  return group;
}

export function setupCardScene(scene, camera, config, textures) {
  const angle = config.angle || 'angle_front';
  const isHolo = config.is_holographic !== false;

  // Posicionamento da Câmera com recuo para margens confortáveis
  if (angle === 'angle_front') {
    camera.position.set(0.7, 0.4, 4.3);
  } else if (angle === 'isometric') {
    camera.position.set(2.2, 1.8, 3.4);
  } else if (angle === 'front_tilt') {
    camera.position.set(0.2, 0.2, 4.2);
  } else if (angle === 'stacked_pair') {
    camera.position.set(0.5, 0.3, 4.3);
  } else {
    camera.position.set(0.7, 0.4, 4.3);
  }
  camera.lookAt(0, 0, 0);

  // Iluminação de Estúdio Especial para Iridescência
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
  scene.add(ambientLight);

  const mainLight = new THREE.DirectionalLight(0xfff5e6, 2.5);
  mainLight.position.set(2.5, 3.5, 3.5);
  scene.add(mainLight);

  const rainbowSpot = new THREE.DirectionalLight(0xe0f7fa, 1.8);
  rainbowSpot.position.set(-3.0, 2.0, 2.0);
  scene.add(rainbowSpot);

  const rimLight = new THREE.DirectionalLight(0xfce4ec, 1.2);
  rimLight.position.set(-1.5, -2.5, -2.0);
  scene.add(rimLight);

  if (textures.art) {
    textures.art.colorSpace = THREE.SRGBColorSpace;
    textures.art.generateMipmaps = true;
    textures.art.minFilter = THREE.LinearMipmapLinearFilter;
  }
  if (textures.back_art) {
    textures.back_art.colorSpace = THREE.SRGBColorSpace;
    textures.back_art.generateMipmaps = true;
    textures.back_art.minFilter = THREE.LinearMipmapLinearFilter;
  }

  if (angle === 'stacked_pair' && textures.back_art) {
    // Modo Duplo: Carta da Frente e Carta do Verso ao lado
    const cardBack = createSingleCardMesh(textures.back_art, textures.art, false);
    cardBack.position.set(-0.55, -0.15, -0.2);
    cardBack.rotation.set(0.1, 0.3, -0.15);
    scene.add(cardBack);

    const cardFront = createSingleCardMesh(textures.art, textures.back_art, isHolo);
    cardFront.position.set(0.45, 0.15, 0.1);
    cardFront.rotation.set(-0.12, -0.25, 0.08);
    scene.add(cardFront);
  } else {
    // Carta Única com Ângulo Dinâmico
    const card = createSingleCardMesh(textures.art, textures.back_art, isHolo);
    if (angle === 'angle_front') {
      card.rotation.set(-0.12, -0.28, 0.06);
    } else if (angle === 'isometric') {
      card.rotation.set(-0.35, -0.45, 0.15);
    } else if (angle === 'front_tilt') {
      card.rotation.set(-0.06, -0.1, 0.02);
    }
    scene.add(card);
  }
}
