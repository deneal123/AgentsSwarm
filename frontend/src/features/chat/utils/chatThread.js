export const createThreadId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (symbol) => {
    const rnd = Math.random() * 16 | 0;
    const value = symbol === 'x' ? rnd : ((rnd & 0x3) | 0x8);
    return value.toString(16);
  });
};
