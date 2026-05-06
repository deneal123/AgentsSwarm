import { useCallback } from 'react';
import { useAuth } from '@context/AuthContext';
import { AuthModal, useAuthModal } from '@features/auth';
import { useGuestSession } from '@hooks/useGuestSession';
import { useProfileDrawer } from './useProfileDrawer';

export function useProfileAndAuthFlow() {
  const { checkLimits, incrementRequests, remainingRequests } = useGuestSession();
  const { isAuthenticated, user, logout } = useAuth();
  const {
    profileDisclosure,
    profileData,
    profileQuota,
    profileMemoryCount,
    setProfileMemoryCount,
    isProfileLoading,
    resolveSessionUserId,
  } = useProfileDrawer({ isAuthenticated, user });
  const { isOpen: isAuthModalOpen, onClose: onAuthModalClose, showAuthModal, modalData } = useAuthModal();

  const ensureGuestLimit = useCallback(() => {
    if (isAuthenticated) {
      return true;
    }
    const limitsCheck = checkLimits();
    if (!limitsCheck.allowed) {
      showAuthModal('Превышен лимит запросов', 'Бесплатные запросы закончились. Войдите, чтобы продолжить.', 'request_limit');
      return false;
    }
    return true;
  }, [checkLimits, isAuthenticated, showAuthModal]);

  return {
    isAuthenticated,
    user,
    logout,
    incrementRequests,
    remainingRequests,
    profileDisclosure,
    profileData,
    profileQuota,
    profileMemoryCount,
    setProfileMemoryCount,
    isProfileLoading,
    resolveSessionUserId,
    isAuthModalOpen,
    onAuthModalClose,
    showAuthModal,
    modalData,
    AuthModal,
    ensureGuestLimit,
  };
}
