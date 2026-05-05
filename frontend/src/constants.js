export const PROJECT_NAME = "GPTHub";
export const PROJECT_VERSION = "1.0.0";
export const COMPANY_NAME = "InCellCorp";
export const PROJECT_AUTHOR = "Команда InCellCorp";
export const CURRENT_YEAR = new Date().getFullYear();
export const SUPPORT_EMAIL = "deneal123@mail.ru";
export const ORG_GITHUB_URL = "https://github.com/Prischli-Drink-Coffee";
export const ORG_VK_URL = "https://vk.com/incellcorp";

export const HERO_TECH_STACK = [
  "FastAPI",
  "PostgreSQL",
  "React",
  "Chakra UI",
  "Docker",
  "Nginx",
  "OpenAI GPT",
  "Redis",
  "WebSocket",
  "MinIO",
  "Prometheus",
  "Grafana",
];

export const HERO_COPY = {
  brandFootnote: `${PROJECT_NAME} — AI Агенты Здоровья`,
  titleHighlight: "вашем питании",
  descriptionPrimary:
    "GPTHub — платформа персональных AI-агентов для здоровья и питания. Общайтесь с умными ассистентами о рационе, тренировках и благополучии — без сложных настроек и медицинских знаний.",
  descriptionSecondary:
    "Искусственный интеллект анализирует ваши предпочтения, цели и состояние здоровья, чтобы дать персональные рекомендации по питанию и образу жизни.",
  authenticatedPrimaryCta: { label: "Начать чат", to: "/chat" },
  authenticatedSecondaryCta: { label: "Открыть чат", to: "/" },
  guestPrimaryCta: { label: "Попробовать", to: "/chat" },
  guestSecondaryCta: { label: "Регистрация", to: "/register" },
  guestFootnote: "Зарегистрируйтесь и получите персональные рекомендации по питанию",
};

export const BENEFITS_CONTENT = {
  title: "Ключевые преимущества",
  subtitle: "Почему выбирают GPTHub?",
  description: "Персональные AI-агенты для здоровья и питания с круглосуточной поддержкой и индивидуальным подходом.",
  items: [
    {
      icon: "CheckCircleIcon",
      title: "Персонализация",
      description: "AI анализирует ваши предпочтения и цели для индивидуальных рекомендаций",
      color: "brand.primary",
    },
    {
      icon: "TimeIcon",
      title: "Круглосуточная поддержка",
      description: "Общайтесь с AI-агентами в любое время без ожидания специалистов",
      color: "brand.secondary",
    },
    {
      icon: "RepeatIcon",
      title: "Непрерывное обучение",
      description: "AI адаптируется к вашим отзывам и улучшает рекомендации со временем",
      color: "#f59e0b",
    },
    {
      icon: "LockIcon",
      title: "Конфиденциальность",
      description: "Ваши данные защищены, а разговоры с AI остаются приватными",
      color: "brand.tertiary",
    },
  ],
};

export const FEATURE_SLIDES = [
  {
    id: 1,
    title: "Персональный AI-агент",
    description:
      "Ваш личный AI-ассистент анализирует ваши предпочтения в еде, цели по здоровью и образ жизни для персональных рекомендаций по питанию.",
    badge: "AI Агент",
    gradient:
      "radial-gradient(circle at 20% 20%, rgba(47,116,255,0.45), rgba(139,92,246,0.25) 40%, rgba(6,11,21,0.8) 80%)",
  },
  {
    id: 2,
    title: "Естественный диалог",
    description:
      "Общайтесь с AI как с человеком — задавайте вопросы о питании, получайте рецепты, советы по здоровью и рекомендации по тренировкам в реальном времени.",
    badge: "Чат",
    gradient:
      "radial-gradient(circle at 80% 30%, rgba(20,184,166,0.35), rgba(47,116,255,0.2) 45%, rgba(6,11,21,0.85) 75%)",
  },
  {
    id: 3,
    title: "Планирование питания",
    description:
      "AI создаёт персональные планы питания, учитывая ваши вкусы, аллергии, цели по весу и состояние здоровья. Получайте готовые рецепты и списки покупок.",
    badge: "Питание",
    gradient:
      "radial-gradient(circle at 50% 60%, rgba(244,114,182,0.35), rgba(47,116,255,0.2) 40%, rgba(6,11,21,0.85) 85%)",
  },
  {
    id: 4,
    title: "Отслеживание прогресса",
    description:
      "Ведите дневник питания, отслеживайте изменения веса и самочувствия. AI анализирует ваши данные и корректирует рекомендации.",
    badge: "Аналитика",
    gradient:
      "radial-gradient(circle at 30% 30%, rgba(139,92,246,0.35), rgba(20,184,166,0.2) 45%, rgba(6,11,21,0.75) 75%)",
  },
  {
    id: 5,
    title: "Конфиденциальность данных",
    description:
      "Ваши разговоры с AI, данные о здоровье и предпочтениях в питании остаются полностью конфиденциальными и защищёнными.",
    badge: "Приватность",
    gradient:
      "radial-gradient(circle at 70% 20%, rgba(236,72,153,0.35), rgba(139,92,246,0.2) 45%, rgba(6,11,21,0.75) 75%)",
  },
];
