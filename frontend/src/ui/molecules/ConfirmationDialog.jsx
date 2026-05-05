import React, { useRef } from "react";
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Button,
  Box,
  VStack,
  Text,
  Icon,
} from "@chakra-ui/react";
import { WarningIcon, DeleteIcon } from "@chakra-ui/icons";
import { MotionBox } from "@ui/motionPrimitives";
import PropTypes from "prop-types";
import { colors, borderRadius } from "@theme/tokens";
import { keyframes } from "@emotion/react";

const pulse = keyframes`
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.05); }
`;

const shake = keyframes`
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
  20%, 40%, 60%, 80% { transform: translateX(2px); }
`;

const variantConfig = {
  danger: {
    icon: DeleteIcon,
    color: "#ef4444",
    gradient: "linear-gradient(135deg, #ef4444, #dc2626)",
    glow: "rgba(239, 68, 68, 0.3)",
  },
  warning: {
    icon: WarningIcon,
    color: "#f59e0b",
    gradient: "linear-gradient(135deg, #f59e0b, #d97706)",
    glow: "rgba(245, 158, 11, 0.3)",
  },
  info: {
    icon: WarningIcon,
    color: colors.brand.primary,
    gradient: `linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary})`,
    glow: `${colors.brand.primary}40`,
  },
};

function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title = "Подтверждение",
  description = "Вы уверены? Это действие нельзя отменить.",
  confirmText = "Удалить",
  cancelText = "Отмена",
  isLoading = false,
  variant = "danger",
}) {
  const cancelRef = useRef();
  const config = variantConfig[variant] || variantConfig.danger;

  return (
    <AlertDialog
      isOpen={isOpen}
      leastDestructiveRef={cancelRef}
      onClose={onClose}
      isCentered
      motionPreset="slideInBottom"
    >
      <AlertDialogOverlay bg="rgba(0, 0, 0, 0.7)" backdropFilter="blur(8px)">
        <MotionBox
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <AlertDialogContent
            bg={colors.background.darkSecondary}
            border="1px solid"
            borderColor="rgba(255,255,255,0.08)"
            borderRadius={borderRadius["2xl"]}
            boxShadow={`0 25px 60px rgba(0,0,0,0.5), 0 0 40px ${config.glow}`}
            maxW="420px"
            mx={4}
            overflow="hidden"
            position="relative"
          >
            {/* Background glow */}
            <Box
              position="absolute"
              top="-50px"
              left="50%"
              transform="translateX(-50%)"
              w="200px"
              h="200px"
              borderRadius="full"
              bg={`radial-gradient(circle, ${config.glow} 0%, transparent 70%)`}
              filter="blur(40px)"
              animation={`${pulse} 3s ease-in-out infinite`}
              pointerEvents="none"
            />

            <AlertDialogHeader pt={8} pb={4} px={8} position="relative">
              <VStack spacing={5}>
                {/* Icon container */}
                <MotionBox
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.1, duration: 0.3 }}
                >
                  <Box
                    p={4}
                    borderRadius={borderRadius.xl}
                    bg={`${config.color}15`}
                    border="1px solid"
                    borderColor={`${config.color}30`}
                    animation={variant === "danger" ? `${shake} 0.5s ease-in-out` : undefined}
                  >
                    <Icon as={config.icon} boxSize={8} color={config.color} />
                  </Box>
                </MotionBox>

                <Text fontSize="xl" fontWeight={600} color={colors.text.primary} textAlign="center">
                  {title}
                </Text>
              </VStack>
            </AlertDialogHeader>

            <AlertDialogBody px={8} pb={6}>
              <Text fontSize="sm" color={colors.text.secondary} textAlign="center" lineHeight="1.7">
                {description}
              </Text>
            </AlertDialogBody>

            <AlertDialogFooter px={8} pb={8} pt={2} display="flex" gap={3} justifyContent="center">
              <MotionBox whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  ref={cancelRef}
                  onClick={onClose}
                  isDisabled={isLoading}
                  variant="ghost"
                  size="lg"
                  borderRadius={borderRadius.xl}
                  px={8}
                  color={colors.text.secondary}
                  bg="rgba(255,255,255,0.05)"
                  border="1px solid"
                  borderColor="rgba(255,255,255,0.1)"
                  _hover={{
                    bg: "rgba(255,255,255,0.08)",
                    borderColor: "rgba(255,255,255,0.15)",
                  }}
                  _disabled={{
                    opacity: 0.5,
                    cursor: "not-allowed",
                  }}
                >
                  {cancelText}
                </Button>
              </MotionBox>

              <MotionBox whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  onClick={onConfirm}
                  isLoading={isLoading}
                  size="lg"
                  borderRadius={borderRadius.xl}
                  px={8}
                  bg={config.gradient}
                  color="white"
                  fontWeight={600}
                  _hover={{
                    bg: config.gradient,
                    boxShadow: `0 8px 25px ${config.glow}`,
                    transform: "translateY(-1px)",
                  }}
                  _active={{
                    transform: "translateY(0)",
                  }}
                  _loading={{
                    bg: config.gradient,
                    opacity: 0.8,
                  }}
                  transition="all 0.2s ease"
                >
                  {confirmText}
                </Button>
              </MotionBox>
            </AlertDialogFooter>
          </AlertDialogContent>
        </MotionBox>
      </AlertDialogOverlay>
    </AlertDialog>
  );
}

ConfirmationDialog.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  title: PropTypes.string,
  description: PropTypes.string,
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  isLoading: PropTypes.bool,
  variant: PropTypes.oneOf(["danger", "warning", "info"]),
};

ConfirmationDialog.defaultProps = {
  title: "Подтверждение",
  description: "Вы уверены? Это действие нельзя отменить.",
  confirmText: "Удалить",
  cancelText: "Отмена",
  isLoading: false,
  variant: "danger",
};

export default ConfirmationDialog;
