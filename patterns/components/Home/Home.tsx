import React from "react";
import { View } from "react-native";

import Following from "@/pages/follow/Follow";
import Discover from "@/pages/discover/Discover";
import BigPostCard from "@/components/bigpostcard/bigpostcard";

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

//will release a more efficient layout in 2.0! shout at me later please abeg