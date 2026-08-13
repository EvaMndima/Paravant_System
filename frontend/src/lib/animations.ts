import type { Variants, Transition } from 'framer-motion';

export const smoothSpring: Transition = {
  type: "spring",
  stiffness: 100,
  damping: 15,
  mass: 1,
};

export const fadeInUp: Variants = {
  initial: {
    opacity: 0,
    y: 20
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: { ...smoothSpring }
  },
  exit: {
    opacity: 0,
    y: -20,
    transition: { duration: 0.2 }
  }
};

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: smoothSpring
  }
};

export const hoverCard = {
  scale: 1.02,
  y: -4,
  transition: { duration: 0.2 }
};

export const tapButton = {
  scale: 0.98,
};
