/**
 * SystemDesign.io Hummingbird Logo
 * Minimalist line-art hummingbird — adapts to theme via currentColor
 */
import React from "react";

interface LogoProps {
  className?: string;
  size?: number;
}

export const Logo: React.FC<LogoProps> = ({ className = "", size = 32 }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 200 200"
    width={size}
    height={size}
    fill="none"
    stroke="currentColor"
    strokeWidth="8"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    {/* Upper wing / leaf */}
    <path d="M 100 30 C 72 28, 52 52, 58 88 C 68 62, 86 50, 108 54 C 118 38, 116 28, 100 30 Z" />
    {/* Lower wing */}
    <path d="M 108 54 C 122 50, 142 54, 150 70 C 140 65, 126 65, 112 74" />
    {/* Body */}
    <path d="M 58 88 C 54 102, 58 118, 74 130 L 88 114 C 78 110, 70 98, 74 86" />
    {/* Beak */}
    <path d="M 88 114 L 108 104 C 118 98, 130 90, 140 78" />
    {/* Head/throat connecting curve */}
    <path d="M 112 74 C 110 84, 108 94, 108 104" />
    {/* Tail */}
    <path d="M 74 130 L 62 150" />
  </svg>
);

export default Logo;
