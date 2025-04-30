import React, { useState, useRef, useEffect } from "react";
import styled from "styled-components";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import { Message } from "../../types";
import { v4 as uuidv4 } from "uuid";

const ChatContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  background: ${({ theme }) => theme.background};
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 10px ${({ theme }) => theme.shadow};
`;

const ChatHeader = styled.div`
  background: ${({ theme }) => theme.primary};
  color: white;
  padding: 16px;
  font-weight: bold;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const ChatBody = styled.div`
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
`;

const ChatFooter = styled.div`
  border-top: 1px solid ${({ theme }) => theme.border};
  padding: 8px 16px;
  background: ${({ theme }) => theme.surface};
`;

const WelcomeMessage = styled.div`
  text-align: center;
  margin: 24px 0;
  color: ${({ theme }) => theme.textSecondary};
`;

const ChatBot: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Hi there! How can I help you today?",
      sender: "bot",
      timestamp: new Date(),
    },
  ]);

  const chatBodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async (text: string) => {
    const newUserMessage: Message = {
      id: uuidv4(),
      text,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, newUserMessage]);

    setTimeout(() => {
      const botResponse: Message = {
        id: uuidv4(),
        text: `Thank you for your message. This is a demo chatbot that would normally connect to a backend API. Your message was: "${text}"`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botResponse]);
    }, 1000);
  };

  return (
    <ChatContainer>
      <ChatHeader>Alltius Assistant</ChatHeader>
      <ChatBody ref={chatBodyRef}>
        {messages.length === 0 ? (
          <WelcomeMessage>Send a message to start chatting</WelcomeMessage>
        ) : (
          messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))
        )}
      </ChatBody>
      <ChatFooter>
        <ChatInput onSendMessage={handleSendMessage} />
      </ChatFooter>
    </ChatContainer>
  );
};

export default ChatBot;
