import React from 'react';
import {
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  Text,
  useDisclosure,
  Box,
  Icon
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { colors } from '@theme/tokens';
import { FiLock, FiCalendar, FiMessageSquare } from 'react-icons/fi';
import { AUTH_PRIMARY_BUTTON_SX } from './authButtonStyles';

function AuthModal({ isOpen, onClose, title, description, onAuth, type = 'general' }) {
  const navigate = useNavigate();

  const handleRegister = () => {
    onClose();
    navigate('/register');
    if (onAuth) onAuth();
  };

  const handleLogin = () => {
    onClose();
    navigate('/login');
    if (onAuth) onAuth();
  };

  const getContentByType = () => {
    switch (type) {
      case 'request_limit':
        return {
          icon: FiMessageSquare,
          title: title || 'Требуется авторизация',
          description: description || 'Лимит гостевых запросов исчерпан. Войдите, чтобы продолжить.'
        };

      case 'calendar_generation':
        return {
          icon: FiCalendar,
          title: title || 'Требуется авторизация',
          description: description || 'Календари доступны только после входа в аккаунт.'
        };

      case 'advanced_features':
        return {
          icon: FiLock,
          title: title || 'Требуется авторизация',
          description: description || 'Эта функция доступна только авторизованным пользователям.'
        };

      default:
        return {
          icon: FiLock,
          title: title || 'Требуется авторизация',
          description: description || 'Войдите или зарегистрируйтесь, чтобы продолжить.'
        };
    }
  };

  const content = getContentByType();
  const IconComponent = content.icon;

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="md">
      <ModalOverlay bg="rgba(0,0,0,0.6)" backdropFilter="blur(6px)" />
      <ModalContent
        bg="rgba(12,12,12,0.96)"
        border="1px solid rgba(255,255,255,0.12)"
        borderRadius="2xl"
        boxShadow="0 24px 60px rgba(0,0,0,0.55)"
        overflow="hidden"
      >
        <ModalHeader
          color={colors.text.primary}
          textAlign="center"
          fontSize="lg"
          fontWeight="700"
          pb={1}
          pt={6}
        >
          <VStack spacing={3}>
            <Box
              p={3}
              borderRadius="full"
              bg="rgba(239,68,68,0.14)"
              border="1px solid rgba(239,68,68,0.35)"
            >
              <Icon
                as={IconComponent}
                boxSize={6}
                color="red.300"
              />
            </Box>
            <Text>{content.title}</Text>
          </VStack>
        </ModalHeader>

        <ModalCloseButton color={colors.text.secondary} />

        <ModalBody pb={6} pt={3}>
          <VStack spacing={5} align="center">
            <Text
              color={colors.text.secondary}
              textAlign="center"
              fontSize="sm"
              lineHeight="1.5"
              maxW="360px"
            >
              {content.description}
            </Text>

            <VStack spacing={3} w="full" maxW="300px">
              <Button
                onClick={handleRegister}
                w="full"
                {...AUTH_PRIMARY_BUTTON_SX}
              >
                Зарегистрироваться
              </Button>

              <Button
                onClick={handleLogin}
                w="full"
                h="46px"
                variant="outline"
                borderColor="rgba(255,255,255,0.24)"
                bg="rgba(255,255,255,0.03)"
                color={colors.text.primary}
                fontWeight="600"
                borderRadius="xl"
                _hover={{ bg: 'rgba(255,255,255,0.08)', borderColor: 'rgba(255,255,255,0.34)' }}
                leftIcon={<Icon as={FiLock} />}
              >
                Войти
              </Button>
            </VStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}

export function useAuthModal() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [modalData, setModalData] = React.useState({});

  const showAuthModal = (title, description, type = 'general', onAuth) => {
    setModalData({ title, description, type, onAuth });
    onOpen();
  };

  return {
    isOpen,
    onClose,
    showAuthModal,
    modalData
  };
}

export default AuthModal;
