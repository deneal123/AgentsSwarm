import React from 'react';
import { VStack } from '@chakra-ui/react';
import TraceSessionCard from './TraceSessionCard';

function TracePanel({ sessions, expandedMap, isCompactTrace, onToggleExpanded }) {
  return (
    <VStack align="stretch" spacing={3} w="100%">
      {sessions.map((session) => (
        <TraceSessionCard
          key={session.id}
          session={session}
          isCompactTrace={isCompactTrace}
          isExpanded={expandedMap[session.id] ?? (session.status === 'running')}
          onToggleExpanded={(expanded) => onToggleExpanded(session.id, expanded)}
        />
      ))}
    </VStack>
  );
}

export default TracePanel;
