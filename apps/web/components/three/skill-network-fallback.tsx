/**
 * Static 2D fallback for the 3D skill-network hero visual — served instead of the
 * Three.js scene on low-end devices, mobile, and prefers-reduced-motion
 * (docs/UI_ARCHITECTURE.md §6). Same visual idea (connected nodes), zero WebGL cost.
 */
export function SkillNetworkFallback() {
  const nodes = [
    { x: 60, y: 40 },
    { x: 180, y: 90 },
    { x: 300, y: 50 },
    { x: 120, y: 180 },
    { x: 260, y: 200 },
    { x: 40, y: 260 },
    { x: 340, y: 150 },
    { x: 200, y: 300 },
  ];
  const edges: [number, number][] = [
    [0, 1],
    [1, 2],
    [1, 3],
    [3, 4],
    [4, 6],
    [3, 5],
    [4, 7],
    [2, 6],
  ];

  return (
    <svg
      viewBox="0 0 380 340"
      className="h-full w-full"
      role="img"
      aria-label="Illustration of connected career and skill nodes"
    >
      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a].x}
          y1={nodes[a].y}
          x2={nodes[b].x}
          y2={nodes[b].y}
          stroke="var(--color-border-strong)"
          strokeWidth={1}
        />
      ))}
      {nodes.map((node, i) => (
        <circle
          key={i}
          cx={node.x}
          cy={node.y}
          r={i % 3 === 0 ? 6 : 4}
          fill={i % 3 === 0 ? "var(--color-primary)" : "var(--color-muted-foreground)"}
        />
      ))}
    </svg>
  );
}
