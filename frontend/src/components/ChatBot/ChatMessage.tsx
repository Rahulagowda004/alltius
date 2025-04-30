import React from "react";
import styled from "styled-components";
import { Message } from "../../types";

interface ChatMessageProps {
  message: Message;
}

const MessageContainer = styled.div<{ isUser: boolean }>`
  display: flex;
  margin-bottom: 16px;
  justify-content: ${({ isUser }) => (isUser ? "flex-end" : "flex-start")};
`;

const MessageBubble = styled.div<{ isUser: boolean }>`
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 18px;
  background-color: ${({ isUser, theme }) =>
    isUser ? theme.primary : theme.surface};
  color: ${({ isUser, theme }) => (isUser ? "#fff" : theme.text)};
  box-shadow: 0 1px 2px ${({ theme }) => theme.shadow};
`;

const TimeStamp = styled.div`
  font-size: 0.7rem;
  margin-top: 4px;
  text-align: right;
  color: ${({ theme }) => theme.textSecondary};
`;

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === "user";
  const formattedTime = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(message.timestamp);

  return (
    <MessageContainer isUser={isUser}>
      <MessageBubble isUser={isUser}>
        {message.text}
        <TimeStamp>{formattedTime}</TimeStamp>
      </MessageBubble>
    </MessageContainer>
  );
};

export default ChatMessage;
