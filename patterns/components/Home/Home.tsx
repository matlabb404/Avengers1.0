import React from "react";
import { View } from "react-native";

import Following from "@/pages/follow/Follow";
import Discover from "@/pages/discover/Discover";

import styles from "./Home.styles";

interface MainHomeProps {
  activePage: string; // Receive activePage from HomeScreen
}

const MainHome = ({ activePage }: MainHomeProps) => {
  // Map link values to components
  const pageComponents: { [key: string]: React.ComponentType } = {
    Following,
    Discover,
  };

  return (
    <View style={styles.activePage}>
      {/* Render the active component */}
      {activePage && React.createElement(pageComponents[activePage])}
    </View>
  );
};

export default MainHome;
