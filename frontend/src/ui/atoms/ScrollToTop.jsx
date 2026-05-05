import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * ScrollToTop - сбрасывает позицию скролла при изменении маршрута
 * Решает проблему когда пользователь оказывается посередине страницы после навигации
 */
function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    // Сброс скролла при изменении маршрута
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "instant", // instant для немедленного перехода, можно использовать "smooth"
    });
  }, [pathname]);

  return null;
}

export default ScrollToTop;
