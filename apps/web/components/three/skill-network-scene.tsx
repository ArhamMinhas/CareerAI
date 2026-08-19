"use client";

import { useMemo, useRef, useState } from "react";
import { Canvas, useFrame, type ThreeElements, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

const VIOLET = new THREE.Color("#8b5cf6");
const VIOLET_BRIGHT = new THREE.Color("#c4b5fd");
const NEUTRAL = "#a1a1aa";

function seededRandom(seed: number) {
  let value = seed;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

type NodeDatum = {
  base: THREE.Vector3;
  phase: number;
  speed: number;
  amplitude: number;
  isHub: boolean;
};

function generateNodes(count: number, radius: number, seed: number): NodeDatum[] {
  const rand = seededRandom(seed);
  const nodes: NodeDatum[] = [];
  for (let i = 0; i < count; i++) {
    // Points distributed inside a sphere volume, biased outward for a fuller silhouette.
    const theta = rand() * Math.PI * 2;
    const phi = Math.acos(2 * rand() - 1);
    const r = radius * (0.55 + rand() * 0.45);
    nodes.push({
      base: new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      ),
      phase: rand() * Math.PI * 2,
      speed: 0.4 + rand() * 0.5,
      amplitude: 0.06 + rand() * 0.08,
      isHub: i % 4 === 0,
    });
  }
  return nodes;
}

function generateEdges(nodes: NodeDatum[]) {
  // Connect each node to its 2 nearest neighbors only — keeps the graph legible and cheap,
  // rather than an O(n^2) web of every point to every point.
  const edges: [number, number][] = [];
  for (let i = 0; i < nodes.length; i++) {
    const distances = nodes
      .map((n, j) => ({ j, d: i === j ? Infinity : nodes[i].base.distanceTo(n.base) }))
      .sort((a, b) => a.d - b.d);
    for (const { j } of distances.slice(0, 2)) {
      const key: [number, number] = i < j ? [i, j] : [j, i];
      if (!edges.some(([a, b]) => a === key[0] && b === key[1])) edges.push(key);
    }
  }
  return edges;
}

/** Sparse, slow-drifting background points — pure depth cue, not a focal element. */
function AmbientParticles({ radius, reduceMotion }: { radius: number; reduceMotion: boolean }) {
  const ref = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const rand = seededRandom(7);
    const count = 60;
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      const r = radius * (1.1 + rand() * 0.9);
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, [radius]);

  useFrame((_, delta) => {
    if (!ref.current || reduceMotion) return;
    ref.current.rotation.y += delta * 0.015;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color={NEUTRAL} size={0.02} transparent opacity={0.35} sizeAttenuation />
    </points>
  );
}

function Nodes({ nodes, reduceMotion }: { nodes: NodeDatum[]; reduceMotion: boolean }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);
  const [hovered, setHovered] = useState<number | null>(null);
  // A plain mutable map read/written every frame in useFrame — not React state, which would
  // mean a setState-per-frame render storm. Declared and used entirely within this component
  // (never passed as a prop) so the React Compiler never sees a ref crossing a render boundary.
  const pulsesRef = useRef(new Map<number, number>());

  useFrame((state) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const t = state.clock.elapsedTime;

    nodes.forEach((node, i) => {
      // Organic per-node float — each node bobs on its own phase/speed/amplitude so the
      // whole network reads as gently alive rather than a rigid rotating solid. Skipped under
      // reduced-motion (ambient, unsolicited movement); hover/click below stay interactive
      // either way since those are user-initiated, not automatic.
      const bob = reduceMotion ? 0 : Math.sin(t * node.speed + node.phase) * node.amplitude;
      dummy.position.copy(node.base).addScaledVector(node.base.clone().normalize(), bob);

      let scale = node.isHub ? 1.6 : 1;
      if (hovered === i) scale *= 1.6;

      const pulseStart = pulsesRef.current.get(i);
      if (pulseStart !== undefined) {
        const elapsed = t - pulseStart;
        const duration = 0.6;
        if (elapsed < duration) {
          scale *= 1 + Math.sin((elapsed / duration) * Math.PI) * 0.9;
        } else {
          pulsesRef.current.delete(i);
        }
      }

      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);

      color.copy(hovered === i ? VIOLET_BRIGHT : VIOLET);
      mesh.setColorAt(i, color);
    });

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  const handlePointerMove = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    if (event.instanceId !== undefined) setHovered(event.instanceId);
  };

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, nodes.length]}
      onPointerMove={handlePointerMove}
      onPointerOut={() => setHovered(null)}
      onClick={(event: ThreeEvent<MouseEvent>) => {
        event.stopPropagation();
        if (event.instanceId !== undefined) {
          pulsesRef.current.set(event.instanceId, performance.now() / 1000);
        }
      }}
    >
      <sphereGeometry args={[0.045, 16, 16]} />
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
}

function Edges({
  nodes,
  edges,
  reduceMotion,
}: {
  nodes: NodeDatum[];
  edges: [number, number][];
  reduceMotion: boolean;
}) {
  const lineRef = useRef<THREE.LineSegments>(null);
  const positions = useMemo(() => new Float32Array(edges.length * 6), [edges.length]);

  useFrame((state) => {
    const line = lineRef.current;
    if (!line) return;
    const t = state.clock.elapsedTime;
    edges.forEach(([a, b], i) => {
      const na = nodes[a];
      const nb = nodes[b];
      const bobA = reduceMotion ? 0 : Math.sin(t * na.speed + na.phase) * na.amplitude;
      const bobB = reduceMotion ? 0 : Math.sin(t * nb.speed + nb.phase) * nb.amplitude;
      const pa = na.base.clone().addScaledVector(na.base.clone().normalize(), bobA);
      const pb = nb.base.clone().addScaledVector(nb.base.clone().normalize(), bobB);
      positions.set([pa.x, pa.y, pa.z, pb.x, pb.y, pb.z], i * 6);
    });
    const attr = line.geometry.getAttribute("position") as THREE.BufferAttribute;
    attr.needsUpdate = true;
  });

  return (
    <lineSegments ref={lineRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial color={NEUTRAL} transparent opacity={0.28} />
    </lineSegments>
  );
}

function NetworkGroup({
  nodeCount,
  radius,
  reduceMotion,
  ...props
}: ThreeElements["group"] & { nodeCount: number; radius: number; reduceMotion: boolean }) {
  const nodes = useMemo(() => generateNodes(nodeCount, radius, 42), [nodeCount, radius]);
  const edges = useMemo(() => generateEdges(nodes), [nodes]);

  return (
    <group {...props}>
      <Nodes nodes={nodes} reduceMotion={reduceMotion} />
      <Edges nodes={nodes} edges={edges} reduceMotion={reduceMotion} />
    </group>
  );
}

export function SkillNetworkScene({
  nodeCount = 28,
  radius = 3.2,
  cameraDistance = 7,
  interactive = true,
  reduceMotion = false,
}: {
  nodeCount?: number;
  radius?: number;
  cameraDistance?: number;
  interactive?: boolean;
  reduceMotion?: boolean;
}) {
  return (
    <Canvas
      camera={{ position: [0, 0, cameraDistance], fov: 45 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
      style={{ touchAction: interactive ? "none" : "auto", cursor: interactive ? "grab" : "default" }}
    >
      <NetworkGroup nodeCount={nodeCount} radius={radius} reduceMotion={reduceMotion} />
      <AmbientParticles radius={radius} reduceMotion={reduceMotion} />
      {interactive ? (
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          enableDamping
          dampingFactor={0.08}
          rotateSpeed={0.5}
          autoRotate={!reduceMotion}
          autoRotateSpeed={0.4}
          minPolarAngle={Math.PI / 2 - 0.6}
          maxPolarAngle={Math.PI / 2 + 0.6}
        />
      ) : null}
    </Canvas>
  );
}
