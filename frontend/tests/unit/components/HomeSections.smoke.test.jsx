import React from "react";
import { render, screen } from "@testing-library/react";
import { ChakraProvider } from "@chakra-ui/react";
import { BrowserRouter } from "react-router-dom";
import {
  HomeBenefitsCanonicalSection,
  HomeHeroCanonicalSection,
  HomeMetricsCanonicalSection,
  HomeWorkspaceCanonicalSection,
} from "@features/home/components/sections";

jest.mock("@features/home/components/SearchInterface", () => () => <div data-testid="search-interface" />);
jest.mock("@features/home/components/HeroBackground", () => () => <div data-testid="hero-background" />);
jest.mock("@features/home/components/BenefitsSection", () => () => <div data-testid="benefits-section" />);
jest.mock("@features/home/components/HomeWorkspaceSection", () => () => <div data-testid="workspace-section" />);
jest.mock("@features/home/components/AuthenticatedMetricsDistributions", () => () => <div data-testid="metrics-section" />);
jest.mock("@ui/assets/common/Logo", () => () => <div data-testid="logo" />);
jest.mock("@ui/atoms/visualPrimitives", () => ({
  GradientText: ({ children }) => <span>{children}</span>,
  ParticlesBackground: () => <div data-testid="particles-background" />,
  FloatingOrbs: () => <div data-testid="floating-orbs" />,
  TiltCard: ({ children }) => <div data-testid="tilt-card">{children}</div>,
}));

const Wrapper = ({ children }) => (
  <BrowserRouter>
    <ChakraProvider>{children}</ChakraProvider>
  </BrowserRouter>
);

describe("home canonical sections smoke", () => {
  it("renders assistant hero variant", () => {
    const { asFragment } = render(
      <Wrapper>
        <HomeHeroCanonicalSection variant="assistant" />
      </Wrapper>,
    );

    expect(screen.getByTestId("hero-background")).toBeInTheDocument();
    expect(screen.getByTestId("search-interface")).toBeInTheDocument();
    expect(asFragment()).toMatchSnapshot();
  });

  it("renders platform hero variant", () => {
    const { asFragment } = render(
      <Wrapper>
        <HomeHeroCanonicalSection variant="platform" isAuthenticated />
      </Wrapper>,
    );

    expect(screen.queryByTestId("search-interface")).not.toBeInTheDocument();
    expect(screen.getByText(/Обработка данных/i)).toBeInTheDocument();
    expect(asFragment()).toMatchSnapshot();
  });

  it("renders benefits canonical wrapper", () => {
    const { asFragment } = render(
      <Wrapper>
        <HomeBenefitsCanonicalSection />
      </Wrapper>,
    );

    expect(screen.getByTestId("benefits-section")).toBeInTheDocument();
    expect(asFragment()).toMatchSnapshot();
  });

  it("renders workspace canonical wrapper", () => {
    const { asFragment } = render(
      <Wrapper>
        <HomeWorkspaceCanonicalSection />
      </Wrapper>,
    );

    expect(screen.getByTestId("workspace-section")).toBeInTheDocument();
    expect(asFragment()).toMatchSnapshot();
  });

  it("renders metrics canonical wrapper", () => {
    const { asFragment } = render(
      <Wrapper>
        <HomeMetricsCanonicalSection isAuthenticated />
      </Wrapper>,
    );

    expect(screen.getByTestId("metrics-section")).toBeInTheDocument();
    expect(asFragment()).toMatchSnapshot();
  });
});
