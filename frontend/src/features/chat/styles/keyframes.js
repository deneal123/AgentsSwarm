import { keyframes } from '@emotion/react';

export const traceItemReveal = keyframes`
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
`;

export const dotPulse = keyframes`
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
`;

export const bgAuroraA = keyframes`
  0%   { transform: translate3d(-6%, -4%, 0) scale(1); opacity: 0.85; }
  50%  { transform: translate3d(8%, 6%, 0) scale(1.15); opacity: 1; }
  100% { transform: translate3d(-6%, -4%, 0) scale(1); opacity: 0.85; }
`;

export const bgAuroraB = keyframes`
  0%   { transform: translate3d(4%, 8%, 0) scale(1.05); opacity: 0.7; }
  50%  { transform: translate3d(-6%, -4%, 0) scale(1); opacity: 0.95; }
  100% { transform: translate3d(4%, 8%, 0) scale(1.05); opacity: 0.7; }
`;

export const bgAuroraC = keyframes`
  0%   { transform: translate3d(0, 0, 0) scale(1); opacity: 0.5; }
  50%  { transform: translate3d(6%, -6%, 0) scale(1.1); opacity: 0.75; }
  100% { transform: translate3d(0, 0, 0) scale(1); opacity: 0.5; }
`;

export const traceRingSpin = keyframes`
  to { transform: rotate(360deg); }
`;

export const traceRingPulse = keyframes`
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.45); }
  50%      { box-shadow: 0 0 0 6px rgba(239,68,68,0); }
`;
