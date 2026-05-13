import React from "react";
import {
  Box,
  Button,
  Flex,
  HStack,
  Icon,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
  VStack,
} from "@chakra-ui/react";
import { FiCheck, FiChevronDown } from "react-icons/fi";
import { borderRadius, chat, colors, typography } from "@theme/tokens";
import { useResponsive } from "@hooks/useResponsive";
import { AUTO_MODE_LABEL, normalizeModelList, resolveModelTriggerLabel } from "../utils/modelSelector";

function ModelSelector({ selectedModel, availableModels, onChange }) {
  const { isMobile } = useResponsive();
  const isAuto = !selectedModel;
  const label = resolveModelTriggerLabel(selectedModel);
  const models = normalizeModelList(availableModels);

  return (
    <Menu matchWidth>
      <MenuButton
        as={Button}
        w={isMobile ? "100%" : "320px"}
        minW={0}
        size="sm"
        borderRadius={borderRadius.md}
        borderWidth="1px"
        borderColor={isAuto ? chat.modelSelector.triggerBorder : chat.modelSelector.triggerBorderActive}
        bg={isAuto ? chat.modelSelector.triggerBg : chat.modelSelector.activeBg}
        color={isAuto ? chat.modelSelector.triggerText : chat.modelSelector.activeText}
        fontFamily={typography.fontFamily.primary}
        fontSize="13px"
        fontWeight="600"
        px={3}
        overflow="visible"
        _hover={{ bg: isAuto ? chat.modelSelector.triggerBgHover : chat.modelSelector.activeBgHover }}
        _active={{ bg: isAuto ? chat.modelSelector.triggerBgHover : chat.modelSelector.activeBgHover }}
      >
        <HStack w="100%" justify="center" spacing={2}>
          {!isAuto && <Icon as={FiCheck} boxSize="12px" color={chat.modelSelector.activeText} flexShrink={0} />}
          <Text noOfLines={1} textAlign="center">{label}</Text>
          <Icon as={FiChevronDown} boxSize="12px" color="currentColor" flexShrink={0} />
        </HStack>
      </MenuButton>
      <MenuList
        bg={chat.modelSelector.menuBg}
        border="1px solid"
        borderColor={chat.modelSelector.menuBorder}
        borderRadius={borderRadius.md}
        py={1}
        maxH="320px"
        overflowY="auto"
      >
        <MenuItem onClick={() => onChange("")} bg="transparent" _hover={{ bg: chat.modelSelector.itemHover }}>
          <HStack justify="space-between" w="100%">
            <Text>{AUTO_MODE_LABEL}</Text>
            {isAuto && <FiCheck />}
          </HStack>
        </MenuItem>
        {models.map((modelId) => {
          const isSelected = selectedModel === modelId;
          return (
            <MenuItem
              key={modelId}
              onClick={() => onChange(modelId)}
              bg={isSelected ? chat.modelSelector.itemSelectedBg : "transparent"}
              color={isSelected ? chat.modelSelector.activeText : colors.text.primary}
              _hover={{ bg: chat.modelSelector.itemHover }}
            >
              <VStack align="stretch" spacing={0} w="100%">
                <Flex justify="space-between" w="100%" gap={3} align="center">
                  <Box minW={0}>
                    <Text noOfLines={1}>{modelId}</Text>
                  </Box>
                  {isSelected && <FiCheck />}
                </Flex>
              </VStack>
            </MenuItem>
          );
        })}
      </MenuList>
    </Menu>
  );
}

export default ModelSelector;
