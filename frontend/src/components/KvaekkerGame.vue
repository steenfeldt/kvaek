<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";

const open = defineModel<boolean>("open", { default: false });

const COLS = 9;
const ROWS = 9;
const CELL = 44;
const W = COLS * CELL;
const H = ROWS * CELL;
const START = { col: 4, row: 8 };

// Rows: 0 goal pond, 1-3 road, 4 median, 5-7 road, 8 start lawn.
interface Lane {
  row: number;
  dir: 1 | -1;
  speed: number;
  carW: number;
  count: number;
  color: string;
}
const LANES: Lane[] = [
  { row: 1, dir: -1, speed: 95, carW: 2, count: 2, color: "#93432a" },
  { row: 2, dir: 1, speed: 70, carW: 1, count: 3, color: "#c96f4a" },
  { row: 3, dir: -1, speed: 120, carW: 1, count: 2, color: "#6b5d4f" },
  { row: 5, dir: 1, speed: 110, carW: 2, count: 2, color: "#b25532" },
  { row: 6, dir: -1, speed: 80, carW: 1, count: 3, color: "#dcb59a" },
  { row: 7, dir: 1, speed: 65, carW: 1, count: 2, color: "#763726" },
];

const canvasEl = ref<HTMLCanvasElement | null>(null);
const score = ref(0);
const lives = ref(3);
const gameOver = ref(false);

const frog = { ...START };
let cars: { lane: Lane; x: number }[] = [];
let speedMul = 1;
let raf = 0;
let lastT = 0;

function reset(full: boolean) {
  frog.col = START.col;
  frog.row = START.row;
  if (full) {
    score.value = 0;
    lives.value = 3;
    gameOver.value = false;
    speedMul = 1;
    cars = LANES.flatMap((lane) =>
      Array.from({ length: lane.count }, (_, i) => ({ lane, x: (W / lane.count) * i })),
    );
  }
}

function move(dc: number, dr: number) {
  if (gameOver.value || !open.value) return;
  frog.col = Math.min(COLS - 1, Math.max(0, frog.col + dc));
  frog.row = Math.min(ROWS - 1, Math.max(0, frog.row + dr));
  if (frog.row === 0) {
    score.value += 100;
    speedMul = Math.min(2.2, speedMul * 1.12);
    reset(false);
  }
}

const KEYS: Record<string, [number, number]> = {
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
};

function onKey(e: KeyboardEvent) {
  const d = KEYS[e.key];
  if (!d) return;
  e.preventDefault();
  move(d[0], d[1]);
}

function tick(t: number) {
  const dt = Math.min(0.05, (t - lastT) / 1000);
  lastT = t;
  if (!gameOver.value) {
    for (const car of cars) {
      car.x += car.lane.dir * car.lane.speed * speedMul * dt;
      const w = car.lane.carW * CELL;
      if (car.lane.dir === 1 && car.x > W) car.x = -w;
      if (car.lane.dir === -1 && car.x < -w) car.x = W;
      if (car.lane.row === frog.row) {
        const fl = frog.col * CELL + 8;
        if (fl < car.x + w - 4 && fl + CELL - 16 > car.x + 4) {
          lives.value -= 1;
          if (lives.value <= 0) gameOver.value = true;
          else reset(false);
        }
      }
    }
  }
  draw();
  raf = requestAnimationFrame(tick);
}

function draw() {
  const ctx = canvasEl.value?.getContext("2d");
  if (!ctx) return;
  for (let r = 0; r < ROWS; r++) {
    const road = LANES.some((l) => l.row === r);
    ctx.fillStyle = road ? "#2b2118" : r === 0 ? "#e8d0bc" : "#f4e8dd";
    ctx.fillRect(0, r * CELL, W, CELL);
    if (road) {
      ctx.strokeStyle = "rgba(253,250,246,.25)";
      ctx.setLineDash([14, 12]);
      ctx.beginPath();
      ctx.moveTo(0, r * CELL);
      ctx.lineTo(W, r * CELL);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
  ctx.font = "26px serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (let c = 0; c < COLS; c += 2) ctx.fillText("🪷", c * CELL + CELL / 2, CELL / 2 + 2);
  for (const car of cars) {
    ctx.fillStyle = car.lane.color;
    ctx.beginPath();
    ctx.roundRect(car.x, car.lane.row * CELL + 8, car.lane.carW * CELL - 6, CELL - 16, 8);
    ctx.fill();
  }
  ctx.font = "30px serif";
  ctx.fillText("🐸", frog.col * CELL + CELL / 2, frog.row * CELL + CELL / 2 + 2);
}

function start() {
  reset(true);
  lastT = performance.now();
  raf = requestAnimationFrame(tick);
  window.addEventListener("keydown", onKey);
}

function stop() {
  cancelAnimationFrame(raf);
  window.removeEventListener("keydown", onKey);
}

watch(open, (o) => (o ? start() : stop()));
onBeforeUnmount(stop);
</script>

<template>
  <UModal v-model:open="open" title="Kvækker 🐸" :description="$t('kvaekker.hint')">
    <template #body>
      <div class="flex flex-col gap-3">
        <div class="flex justify-between text-sm font-medium">
          <span>{{ $t("kvaekker.score") }}: {{ score }}</span>
          <span>{{ "🐸".repeat(Math.max(0, lives)) }}</span>
        </div>
        <div class="relative">
          <canvas
            ref="canvasEl"
            :width="W"
            :height="H"
            class="mx-auto block w-full max-w-[396px] rounded-lg"
          />
          <div
            v-if="gameOver"
            class="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-lg bg-ink-900/70 text-white"
          >
            <p class="text-xl font-semibold">{{ $t("kvaekker.gameOver") }}</p>
            <p class="text-sm">{{ $t("kvaekker.score") }}: {{ score }}</p>
            <UButton @click="reset(true)">{{ $t("kvaekker.playAgain") }}</UButton>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-1 self-center sm:hidden">
          <span />
          <UButton variant="soft" color="neutral" square @click="move(0, -1)">↑</UButton>
          <span />
          <UButton variant="soft" color="neutral" square @click="move(-1, 0)">←</UButton>
          <UButton variant="soft" color="neutral" square @click="move(0, 1)">↓</UButton>
          <UButton variant="soft" color="neutral" square @click="move(1, 0)">→</UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>
