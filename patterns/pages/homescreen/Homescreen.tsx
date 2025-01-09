import React, { useEffect, useRef, useState } from "react";
import { View, Animated, Dimensions } from "react-native";
import Dropdown from "@/components/Dropdown/Dropdown";
import MainHome from "@/components/Home/Home";
import Footer from "@/components/Footer/Footer";
import styles from "./homescreen.style";
import { check_user } from "@/actions/user";
import Post from "../post/Post";
import Search from "../search/Search";
import Profile from "../profile/Profile";

interface HomeProps {
    navigation: any;
}

const HomeHeaders = [
    { link: "Discover", value: "Discover", isActive: true },
    { link: "Following", value: "Follow", isActive: false },
];

const PostHeaders = [{ link: "Post", value: "Post", isActive: true }];
const SearchHeaders = [{ link: "Search", value: "Search", isActive: true }];
const ProfileHeaders = [{ link: "Profile", value: "Profile", isActive: true }];

const HomeScreen = ({ navigation }: HomeProps) => {
    const [activeComp, setActiveComp] = useState<string>("Home");
    const [activePage, setActivePage] = useState<string>("Discover");

    const [animatedValues, setAnimatedValues] = useState(0);

    const screenHeight = Math.floor(Dimensions.get("window").height);
    const halfScreenHeight = Math.floor(screenHeight / 2);

    // Shared animated value for dropdown height
    const animatedValue = useRef(new Animated.Value(0)).current;

    // Interpolated zIndex for Footer based on dropdown height
    const footerZIndex = animatedValue.interpolate({
        inputRange: [0, Math.floor(halfScreenHeight)],
        outputRange: [101, 0], // Footer on top when dropdown is small
        extrapolate: "clamp",
    });

    useEffect(() => {
        const validateUser = async () => {
            const isValid = await check_user();
            if (!isValid) {
                console.log("User is not authenticated. Redirecting to login...");
                navigation.navigate("Login");
            }
        };

        validateUser();
    }, []);

    const renderActivePage = () => {
        switch (activeComp) {
            case "Post":
                return <Post />;
            case "Search":
                return <Search />;
            case "Profile":
                return <Profile />;
            default:
                return <MainHome activePage={activePage} />;
        }
    };

    const getHeaders = () => {
        if (activeComp === "Post") return PostHeaders;
        if (activeComp === "Search") return SearchHeaders;
        if (activeComp === "Profile") return ProfileHeaders;
        return HomeHeaders;
    };

    const updatedHeaders = getHeaders().map((header) => ({
        ...header,
        isActive: header.link === activePage,
    }));

    const handleNavigationChange = (newActiveComp: string, newActivePage?: string) => {
        setActiveComp(newActiveComp);
        if (newActivePage) {
            setActivePage(newActivePage);
        }
    };

    return (
        <View style={{ flex: 1 }}>
            {/* Dropdown with animatedValue passed as prop */}
            <View style={styles.dropdownContainer}>
                <Dropdown
                    headers={updatedHeaders}
                    navigation={{
                        navigate: (link: string) => setActivePage(link),
                    }}
                    animatedValues={animatedValue} // Pass shared animated value
                    setAnimatedValues={setAnimatedValues}
                />
            </View>
            {/* Render active component */}
            <View style={{
                flex: 1,
                width: '100%',
                maxHeight: screenHeight - 70,
            }}>
                {renderActivePage()}
            </View>
            {/* Footer with dynamic zIndex */}
            <Animated.View
                style={{
                    zIndex: footerZIndex,
                    position: "absolute",
                    bottom: 0,
                    width: "100%",
                }}
            >
                <Footer activePage={activeComp} onNavigate={handleNavigationChange} />
            </Animated.View>
        </View>
    );
};

export default HomeScreen;
