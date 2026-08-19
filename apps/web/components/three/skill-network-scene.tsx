"use client";

import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, type ThreeElements } from "@react-three/fiber";
import * as THREE from "three";

const NODE_COUNT = 28;
const RADIUS = 3.2;
const VIOLET = "#8b5cf6";
const NEUTRAL = "#a1a1aa";

function seededRandom(seed: number) {
  let value = seed;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function generateNodes() {
  const rand = seededRandom(42);
  const nodes: THREE.Vector3[] = [];
  for (let i = 0; i < NODE_COUNT; i++) {
    // Points distributed inside a sphere volume, biased outward for a fuller silhouette.
    const theta = rand() * Math.PI * 2;
    const phi = Math.acos(2 * rand() - 1);
    const r = RADIUS * (0.55 + rand() * 0.45);
    nodes.push(
      new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      )
    );
  }
  return nodes;
}

function generateEdges(nodes: THREE.Vector3[]) {
  // Connect each node to its 2 nearest neighbors only — keeps the graph legible and cheap,
  // rather than an O(n^2) web of every point to every point.
  const edges: [number, number][] = [];
  for (let i = 0; i < nodes.length; i++) {
    const distances = nodes
      .map((n, j) => ({ j, d: i === j ? Infinity : nodes[i].distanceTo(n) }))
      .sort((a, b) => a.d - b.d);
    for (const { j } of distances.slice(0, 2)) {
      const key: [number, number] = i < j ? [i, j] : [j, i];
      if (!edges.some(([a, b]) => a === key[0] && b === key[1])) edges.push(key);
    }
  }
  return edges;
}

function Nodes({ nodes }: { nodes: THREE.Vector3[] }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Mutating the instanced mesh's transform buffer is an imperative side effect on a Three.js
  // object, not render output — belongs in an effect, not useMemo (which runs during render).
  useEffect(() => {
    if (!meshRef.current) return;
    nodes.forEach((pos, i) => {
      dummy.position.copy(pos);
      const scale = i % 4 === 0 ? 1.6 : 1;
      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [nodes, dummy]);

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, nodes.length]}>
      <sphereGeometry args={[0.045, 12, 12]} />
      <meshBasicMaterial color={VIOLET} />
    </instancedMesh>
  );
}

function Edges({ nodes, edges }: { nodes: THREE.Vector3[]; edges: [number, number][] }) {
  const positions = useMemo(() => {
    const arr = new Float32Array(edges.length * 6);
    edges.forEach(([a, b], i) => {
      arr.set([nodes[a].x, nodes[a].y, nodes[a].z, nodes[b].x, nodes[b].y, nodes[b].z], i * 6);
    });
    return arr;
  }, [nodes, edges]);

  return (
    <lineSegments>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial color={NEUTRAL} transparent opacity={0.25} />
    </lineSegments>
  );
}

function NetworkGroup(props: ThreeElements["group"]) {
  const groupRef = useRef<THREE.Group>(null);
  const nodes = useMemo(() => generateNodes(), []);
  const edges = useMemo(() => generateEdges(nodes), [nodes]);

  useFrame((state) => {
    if (!groupRef.current) return;
    // Slow ambient rotation plus a subtle tilt toward the pointer — motivated: signals
    // "alive / intelligent system," not decoration for its own sake.
    groupRef.current.rotation.y += 0.0015;
    groupRef.current.rotation.x = THREE.MathUtils.lerp(
      groupRef.current.rotation.x,
      state.pointer.y * 0.15,
      0.02
    );
    groupRef.current.rotation.z = THREE.MathUtils.lerp(
      groupRef.current.rotation.z,
      -state.pointer.x * 0.1,
      0.02
    );
  });

  return (
    <group ref={groupRef} {...props}>
      <Nodes nodes={nodes} />
      <Edges nodes={nodes} edges={edges} />
    </group>
  );
}

export function SkillNetworkScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 7], fov: 45 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
    >
      <NetworkGroup />
    </Canvas>
  );
}
