# Review 2 interactive demo

This frontend turns the Team 1 research evidence into a guided professor-facing walkthrough. It provides scenario selection, an object-link explorer, flattening and COOC comparisons, a runnable precomputed anomaly benchmark, and an intervention simulator.

## Local run

```bash
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`.

## Production build

```bash
pnpm build
```

The interface uses packaged synthetic values and makes no network request to Educational Capstone Portal.

