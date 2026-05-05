import React, { Suspense, lazy } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Center, Spinner } from "@chakra-ui/react";
import PublicLayout from "./ui/layout/PublicLayout";
import ErrorBoundary from "./ui/molecules/ErrorBoundary";

// Именованные чанки для лучшего кеширования и отладки
const LoginPage = lazy(() => import(/* webpackChunkName: "login" */ "@pages/login"));
const SignUpPage = lazy(() => import(/* webpackChunkName: "signup" */ "@pages/signup"));
const NotFoundPage = lazy(() => import(/* webpackChunkName: "notfound" */ "@pages/notFound"));
const HomePage = lazy(() => import(/* webpackChunkName: "home" */ "@pages/home"));
const InfoPage = lazy(() => import(/* webpackChunkName: "info" */ "@pages/info"));
const DocumentsPage = lazy(() => import(/* webpackChunkName: "documents" */ "@features/documents/DocumentsPage"));
const ChatPage = lazy(() => import(/* webpackChunkName: "chat" */ "@pages/chat"));

const router = createBrowserRouter([
  {
    path: "/",
    element: <PublicLayout />,
    children: [
      { index: true, element: <ChatPage /> },
      { path: "home", element: <HomePage /> },
      { path: "info", element: <InfoPage /> },
      { path: "documents", element: <DocumentsPage /> },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <SignUpPage /> },
      { path: "chat/:threadId", element: <ChatPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);

function App() {
  return (
    <ErrorBoundary level="page">
      <Suspense
        fallback={
          <Center h="100vh">
            <Spinner size="lg" />
          </Center>
        }
      >
        <RouterProvider router={router} />
      </Suspense>
    </ErrorBoundary>
  );
}

export default App;
