import { useDisclosure } from '@chakra-ui/react';
import { useState } from 'react';

export function useChatDrawersState(profileDisclosure) {
  const sidebarDisclosure = useDisclosure();
  const memoryDisclosure = useDisclosure();
  const settingsDisclosure = useDisclosure();
  const [memoryFacts, setMemoryFacts] = useState([]);

  return {
    state: {
      sidebarDisclosure,
      memoryDisclosure,
      settingsDisclosure,
      profileDisclosure,
      memoryFacts,
    },
    actions: {
      setMemoryFacts,
    },
  };
}
