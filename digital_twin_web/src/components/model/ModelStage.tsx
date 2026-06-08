import { Html, OrbitControls, PerspectiveCamera, useGLTF } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import { Alert } from 'antd';
import { memo, Suspense, useMemo, useRef } from 'react';
import { Box3, Vector3, type Group } from 'three';

import { DIGITAL_TWIN_MODEL_URL } from '@/config/runtime';

interface ModelStageProps {
  modelUrl: string;
}

const CAMERA_POSITION: [number, number, number] = [0, 2.55, 9.35];
const CAMERA_TARGET: [number, number, number] = [0, 0.22, 0];

const LoadedModel = ({ modelUrl }: ModelStageProps) => {
  const groupRef = useRef<Group>(null);
  const gltf = useGLTF(modelUrl);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.1;
    }
  });

  const clonedScene = useMemo(() => {
    const scene = gltf.scene.clone();
    const box = new Box3().setFromObject(scene);
    const center = box.getCenter(new Vector3());
    const size = box.getSize(new Vector3());
    const maxAxis = Math.max(size.x, size.y, size.z) || 1;
    const scale = 4.4 / maxAxis;
    scene.position.sub(center);
    scene.scale.setScalar(scale);
    scene.position.y -= size.y * scale * 0.08;
    return scene;
  }, [gltf.scene]);

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <primitive object={clonedScene} />
    </group>
  );
};

const StageFallback = () => (
  <Html center>
    <div className='model-loading'>正在加载 3D 模型...</div>
  </Html>
);

const ModelStage = ({ modelUrl }: ModelStageProps) => {
  if (!modelUrl) {
    return <Alert type='warning' showIcon message='未检测到可用的 3D 模型路径。' />;
  }

  return (
    <div className='model-stage'>
      <div className='model-stage__header'>
        <div>
          <span className='model-stage__label'>数字孪生</span>
          <h2>通佳 TH400/SH 注塑机</h2>
        </div>
        <div className='model-stage__legend'>
          <span>支持鼠标拖拽缩放</span>
          <span>自动慢速旋转</span>
        </div>
      </div>
      <div className='model-stage__canvas'>
        <Canvas
          dpr={1}
          gl={{ alpha: true, antialias: false, powerPreference: 'high-performance' }}
          performance={{ min: 0.8 }}
          resize={{ offsetSize: true }}
        >
          <fog attach='fog' args={['#071531', 18, 44]} />
          <PerspectiveCamera makeDefault position={CAMERA_POSITION} fov={28} />
          <ambientLight intensity={1.65} color='#8fc8ff' />
          <directionalLight position={[8, 12, 6]} intensity={2.6} color='#cfe8ff' />
          <pointLight position={[-8, 4, -5]} intensity={18} color='#38d7ff' />
          <pointLight position={[10, 2, 5]} intensity={12} color='#3f8dff' />
          <Suspense fallback={<StageFallback />}>
            <LoadedModel modelUrl={modelUrl} />
          </Suspense>
          <OrbitControls
            enablePan={false}
            autoRotate={false}
            target={CAMERA_TARGET}
            minDistance={4.5}
            maxDistance={12}
            minPolarAngle={Math.PI / 3.6}
            maxPolarAngle={Math.PI / 2.08}
          />
        </Canvas>
      </div>
    </div>
  );
};

useGLTF.preload(DIGITAL_TWIN_MODEL_URL);

export default memo(ModelStage);
