let started = Date.now();
let offset = 0;
let speed = 1;
let scenario = "healthy";
const initial = { speed: 1, scenario: "healthy" };
let snapshot = initial;
const listeners = new Set<() => void>();
export const subscribeDemo = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};
export const demoSnapshot = () => snapshot;
export const demoServerSnapshot = () => initial;
export const demoSeconds = () =>
  Math.min(3600, offset + ((Date.now() - started) / 1000) * speed);
export function configureDemo(
  nextSpeed: number,
  nextScenario: string,
  reset = false,
) {
  offset = reset ? 0 : demoSeconds();
  started = Date.now();
  speed = nextSpeed;
  scenario = nextScenario;
  snapshot = { speed, scenario };
  listeners.forEach((listener) => listener());
}
export function demoQuery() {
  return new URLSearchParams({
    demo_seconds: String(Math.floor(demoSeconds())),
    demo_scenario: scenario,
  });
}
