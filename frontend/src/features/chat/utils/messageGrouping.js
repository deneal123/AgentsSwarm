import { format, isToday, isYesterday, isThisWeek } from 'date-fns';
import { ru } from 'date-fns/locale';

export function getDateLabel(date) {
  if (isToday(date)) {
    return 'Сегодня';
  }

  if (isYesterday(date)) {
    return 'Вчера';
  }

  if (isThisWeek(date)) {
    return format(date, 'EEEE', { locale: ru });
  }

  return format(date, 'd MMMM yyyy', { locale: ru });
}

export function groupMessagesBySender(messages) {
  if (!messages || messages.length === 0) return [];

  const groups = [];
  let currentGroup = {
    sender: messages[0].type,
    messages: [messages[0]]
  };

  for (let i = 1; i < messages.length; i++) {
    const message = messages[i];

    if (message.type === currentGroup.sender) {
      currentGroup.messages.push(message);
    } else {
      groups.push(currentGroup);
      currentGroup = {
        sender: message.type,
        messages: [message]
      };
    }
  }

  groups.push(currentGroup);

  return groups;
}
