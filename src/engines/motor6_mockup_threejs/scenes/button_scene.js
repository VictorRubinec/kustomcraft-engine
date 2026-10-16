import * as THREE from 'three';

/**
 * Cria a geometria abaulada (domed cap) de um botton americano colecionável.
 */
function createButtonCapGeometry(radius = 1.0, domeHeight = 0.16) {
  const geo = new THREE.CircleGeometry(radius, 64, 16);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const r = Math.sqrt(x * x + y * y) / radius;
    // Curvatura esférica/parabólica suave e progressiva
    const z = (1.0 - Math.pow(r, 2.0)) * domeHeight;
    pos.setZ(i, z);
  }
  geo.computeVertexNormals();
  return geo;
}

/**
 * Cria um botton completo com calota de poliéster de máxima área útil (94%+),
 * aro metálico fino chanfrado e sombra de contato suave.
 */
function createSingleButton(textures, config, radius = 1.0) {
  const group = new THREE.Group();

  // 1. Calota Frontal com Película de Poliéster (Mylar) - Reflexo acetinado em arco suave
  const capGeo = createButtonCapGeometry(radius, 0.16 * radius);
  const capMat = new THREE.MeshPhysicalMaterial({
    map: textures.art || null,
    color: textures.art ? 0xffffff : 0x3b59ec,
    roughness: 0.12,
    metalness: 0.02,
    clearcoat: 0.85,
    clearcoatRoughness: 0.14,
    reflectivity: 0.90,
  });
  const capMesh = new THREE.Mesh(capGeo, capMat);
  group.add(capMesh);

  // 2. Chanfro Periférico Metálico Milimétrico Ultrafino (ocupa apenas ~1.5-2% da borda)
  const rimGeo = new THREE.CylinderGeometry(radius * 1.008, radius * 1.002, 0.020 * radius, 64, 1, true);
  const rimMat = new THREE.MeshStandardMaterial({
    color: 0xd8dce4,
    metalness: 0.88,
    roughness: 0.32,
  });
  const rimMesh = new THREE.Mesh(rimGeo, rimMat);
  rimMesh.rotation.x = Math.PI / 2;
  rimMesh.position.z = -0.010 * radius;
  group.add(rimMesh);

  // 3. Fundo Metálico de Folha de Flandres (Tinplate) com Alfinete
  const backGeo = new THREE.CircleGeometry(radius * 0.99, 64);
  const backMat = new THREE.MeshStandardMaterial({
    color: 0xc8ccd4,
    metalness: 0.85,
    roughness: 0.38,
    side: THREE.BackSide,
  });
  const backMesh = new THREE.Mesh(backGeo, backMat);
  backMesh.position.z = -0.03 * radius;
  group.add(backMesh);

  // 4. Sombra Projetada Suave
  const shadowCanvas = document.createElement('canvas');
  shadowCanvas.width = 128;
  shadowCanvas.height = 128;
  const sCtx = shadowCanvas.getContext('2d');
  const grad = sCtx.createRadialGradient(64, 64, 20, 64, 64, 60);
  grad.addColorStop(0, 'rgba(15, 8, 25, 0.42)');
  grad.addColorStop(0.55, 'rgba(15, 8, 25, 0.12)');
  grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
  sCtx.fillStyle = grad;
  sCtx.fillRect(0, 0, 128, 128);

  const shadowTex = new THREE.CanvasTexture(shadowCanvas);
  const shadowGeo = new THREE.PlaneGeometry(radius * 2.5, radius * 2.5);
  const shadowMat = new THREE.MeshBasicMaterial({
    map: shadowTex,
    transparent: true,
    opacity: 0.75,
    depthWrite: false,
  });
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
  shadowMesh.position.set(0.06 * radius, -0.06 * radius, -0.08 * radius);
  group.add(shadowMesh);

  return group;
}

export function setupButtonScene(scene, camera, config, textures) {
  const angle = config.angle || 'hero';
  const sizeMm = config.size_mm || config.button_size || 44;
  const scaleFactor = sizeMm === 32 ? 0.82 : sizeMm === 58 ? 1.22 : 1.0;

  // Iluminação de Estúdio Suave - Sem ponto cego ou flash duro sobre a tipografia
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.25);
  scene.add(ambientLight);

  // Luz principal superior suave em ângulo difuso: cria arco especular sutil na cúpula
  const keyLight = new THREE.DirectionalLight(0xfffaee, 1.2);
  keyLight.position.set(1.5, 5.5, 2.2);
  scene.add(keyLight);

  // Luz direcional em fita diagonal suave para arco especular clássico da película Mylar
  const stripLight = new THREE.DirectionalLight(0xffffff, 1.35);
  stripLight.position.set(1.8, 4.5, 3.2);
  scene.add(stripLight);

  // Luz suave de recorte lateral
  const rimLight = new THREE.DirectionalLight(0xddeeff, 0.7);
  rimLight.position.set(-3.5, 1.5, 2.0);
  scene.add(rimLight);

  // Luz suave de preenchimento inferior
  const fillLight = new THREE.DirectionalLight(0xffeedd, 0.5);
  fillLight.position.set(0.0, -3.0, 2.0);
  scene.add(fillLight);

  if (angle === 'grid' || angle === 'grid_2x3') {
    // Modo Grid 2x3 (Kit de 6 bottons colecionáveis)
    // Câmera isométrica com pitch -10° e yaw +8° para destacar tridimensionalidade e volume abaulado
    camera.position.set(1.1, 1.4, 7.8);
    camera.lookAt(0.0, 0.0, 0.0);

    const cols = [-0.95, 0.95];
    const rows = [1.55, 0.0, -1.55];
    const buttonScale = 0.72 * scaleFactor;

    let index = 0;
    for (const r of rows) {
      for (const c of cols) {
        const artForBtn = (textures.arts && textures.arts[index]) ? textures.arts[index] : textures.art;
        const btn = createSingleButton({ art: artForBtn }, config, 1.0);
        btn.scale.set(buttonScale, buttonScale, buttonScale);
        btn.position.set(c, r, 0);

        // Variação orgânica sutil de inclinação em cada botton do kit
        const rotX = -0.15 + (index % 3) * 0.03;
        const rotY = 0.12 - (index % 2) * 0.22;
        const rotZ = ((index * 37) % 16 - 8) * (Math.PI / 180);
        btn.rotation.set(rotX, rotY, rotZ);

        scene.add(btn);
        index++;
      }
    }
  } else {
    // Modo Hero Individual (Destaque único fotorrealista)
    camera.position.set(0.28, 0.28, 3.8);
    camera.lookAt(0, 0, 0);

    const btn = createSingleButton(textures, config, 1.0);
    btn.scale.set(scaleFactor, scaleFactor, scaleFactor);
    // Inclinação suave para destacar o volume 3D com o arco especular na borda superior
    btn.rotation.set(-0.20, 0.22, -0.05);
    scene.add(btn);
  }
}
