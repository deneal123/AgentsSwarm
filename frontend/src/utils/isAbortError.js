export default function isAbortError(error) {
  if (!error) return false;

  if (error.name === "AbortError" || error.name === "CanceledError") {
    return true;
  }

  if (typeof error.code === "string" && error.code.toUpperCase() === "ERR_CANCELED") {
    return true;
  }

  if (error.__CANCEL__ === true) {
    return true;
  }

  return false;
}
