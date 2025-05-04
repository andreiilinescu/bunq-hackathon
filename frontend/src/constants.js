const LOCALHOST_URL = import.meta.env.VITE_LOCALHOST_URL;
const SERVER_URL = import.meta.env.VITE_SERVER_URL;

export const IS_DEVELOPMENT = import.meta.env.MODE === "development";
export const IS_PRODUCTION = !IS_DEVELOPMENT;
console.log(IS_PRODUCTION);
export const BACKEND_URL = IS_PRODUCTION ? SERVER_URL : LOCALHOST_URL;
export const BACKEND_URL_CHAT = `${BACKEND_URL}/chat`;
export const BACKEND_URL_VOICE = `${BACKEND_URL}/voice`;
