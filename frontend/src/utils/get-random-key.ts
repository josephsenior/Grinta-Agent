export const getRandomKey = (obj: Record<string, string>) => {
  const keys = Object.keys(obj);
  return keys[Math.floor(Math.random() * keys.length)];
};
