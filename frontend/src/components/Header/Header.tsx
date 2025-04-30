import React from "react";
import styled from "styled-components";
import ThemeToggle from "./ThemeToggle";
import { ThemeMode } from "../../types";

interface HeaderProps {
  theme: ThemeMode;
  toggleTheme: () => void;
}

const HeaderContainer = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background-color: ${({ theme }) => theme.surface};
  box-shadow: 0 2px 4px ${({ theme }) => theme.shadow};
`;

const Logo = styled.div`
  font-size: 1.5rem;
  font-weight: bold;
  color: ${({ theme }) => theme.primary};
  display: flex;
  align-items: center;
  gap: 10px;
`;

const LogoIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"
      fill="currentColor"
    />
  </svg>
);

const Controls = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
`;

const Header: React.FC<HeaderProps> = ({ theme, toggleTheme }) => {
  return (
    <HeaderContainer>
      <Logo>
        <LogoIcon />
        Alltius
      </Logo>
      <Controls>
        <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
      </Controls>
    </HeaderContainer>
  );
};

export default Header;
