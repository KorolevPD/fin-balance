export function createInitialState() {
  return {
    items: [],
    updatedAt: null,
  };
}

if (typeof document !== "undefined") {
  const statusElement = document.querySelector("#status");

  if (statusElement) {
    const state = createInitialState();
    statusElement.dataset.itemsCount = String(state.items.length);
  }
}
