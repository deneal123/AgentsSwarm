import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LoginPage from '@pages/login';

const mockLogin = jest.fn();
const mockNavigateState = { refreshSession: jest.fn(), setAuthenticated: jest.fn() };

jest.mock('@api', () => ({ login: (...args) => mockLogin(...args) }));
jest.mock('@context/AuthContext', () => ({ useAuth: () => mockNavigateState }));

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <ChakraProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>HOME</div>} />
        </Routes>
      </ChakraProvider>
    </MemoryRouter>
  );
}

describe('Auth integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('allows user to login and redirects to home', async () => {
    mockLogin.mockResolvedValue({ ok: true });
    mockNavigateState.refreshSession.mockResolvedValue();

    renderLogin();

    await userEvent.type(screen.getByLabelText(/e-mail/i), 'user@test.dev');
    await userEvent.type(screen.getByLabelText(/пароль/i), 'secret123');
    await userEvent.click(screen.getByRole('button', { name: /войти/i }));

    await waitFor(() => expect(screen.getByText('HOME')).toBeInTheDocument());
    expect(mockLogin).toHaveBeenCalledWith({ email: 'user@test.dev', password: 'secret123' });
  });
});
