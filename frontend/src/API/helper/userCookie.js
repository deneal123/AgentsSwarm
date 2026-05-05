import Cookies from "js-cookie";

export const getToken = () => {
  const token = Cookies.get("auth_token");
  if (token === undefined) {
    return token;
  }
  return `Bearer ${token}`;
};

export const setUser = (user) => {
  // Backend automatically sets auth_token cookie via set_cookie
  // We don't need to manually set it
  if (user.userEmail) {
    Cookies.set("userEmail", user.userEmail, { expires: 365 ** 2 });
  }
};

export const deleteUser = () => {
  Cookies.remove("auth_token");
  Cookies.remove("userEmail");
};
