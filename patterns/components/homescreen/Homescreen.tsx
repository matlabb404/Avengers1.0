import React, { useEffect, useRef, useState } from "react";
import { View, Animated, Dimensions, SafeAreaView } from "react-native";
import Dropdown from "@/components/Dropdown/Dropdown";
import MainHome from "@/components/Home/Home";
import Footer from "@/components/Footer/Footer";
import styles from "./homescreen.style";
import { check_user } from "@/actions/user";
import Post from "../../pages/post/Post";
import Search from "../../pages/search/Search";
import Profile from "../../pages/profile/Profile";
import Chat from "@/pages/chat/Chat";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { connect } from "react-redux";

const MainStack = createNativeStackNavigator();

interface HomeProps {
    navigation: any;
    dropdownOpened: boolean;
    dropdownStatic: boolean;
}

const HomeHeaders = [
    { link: "Discover", value: "Discover", isActive: true },
    { link: "Following", value: "Follow", isActive: false },
];

const PostHeaders = [{ link: "Post", value: "Post", isActive: true }];
const SearchHeaders = [{ link: "Search", value: "Search", isActive: true }];
const ProfileHeaders = [{ link: "Profile", value: "Profile", isActive: true }];

const HomeScreen = ({ navigation, dropdownOpened, dropdownStatic }: HomeProps) => {
    const [activeComp, setActiveComp] = useState<string>("Main");
    const [activePage, setActivePage] = useState<string>("Discover");

    const screenHeight = Math.floor(Dimensions.get("window").height);
    const halfScreenHeight = Math.floor(screenHeight / 2);

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

    useEffect(() => {
        switch (activeComp) {
            case "Post":
                navigation.navigate("HomeScreen", {
                    screen: "Post",
                });
                break;
            case "Search":
                navigation.navigate("HomeScreen", {
                    screen: "Search",
                });
                break;
            case "Profile":
                navigation.navigate("HomeScreen", {
                    screen: "Profile",
                });
                break;
            default:
                navigation.navigate("HomeScreen", {
                    screen: "Main",
                    params: {
                        activePage: activePage,
                    },
                });
                break;
        }
    }, [activeComp]);

    const renderActivePage = () => {
        return activeComp;
    };

    const getHeaders = () => {
        switch (activeComp) {
            case "Post":
                return PostHeaders;
            case "Search":
                return SearchHeaders;
            case "Profile":
                return ProfileHeaders;
            default:
                return HomeHeaders;
        }
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
        <SafeAreaView style={{ flex: 1 }}>
            {/* Dropdown with animatedValue passed as prop */}
            <View style={styles.dropdownContainer}>
                <Dropdown
                    headers={updatedHeaders}
                    navigation={{
                        navigate: (link: string) => setActivePage(link),
                    }}
                />
            </View>
            {/* Render active component */}
            <View style={{
                flex: 1,
                width: '100%',
                maxHeight: screenHeight - 70,
            }}>
                <MainStack.Navigator
                    initialRouteName={'Main'}
                    screenOptions={{
                        headerShown: false, // Enable if custom header is needed
                    }}
                >
                    <MainStack.Screen name="Main">
                        {(props) => <MainHome {...props} activePage={activePage} />}
                    </MainStack.Screen>
                    <MainStack.Screen name="Profile" component={Profile} />
                    <MainStack.Screen name="Search" component={Search} />
                    <MainStack.Screen name="Post" component={Post} />
                    <MainStack.Screen name="Chat" component={Chat} />
                </MainStack.Navigator>
            </View>
            {/* Footer with dynamic zIndex */}
        <Animated.View
            style={{
                zIndex: (dropdownOpened && dropdownStatic) || !dropdownStatic ? 0 : 101,
                position: "absolute",
                bottom: 0,
                width: "100%",
            }}
        >
            <Footer activePage={activeComp} onNavigate={handleNavigationChange} />
        </Animated.View>
        </SafeAreaView>
    );
};

interface StoreState {
    navigation: {
        dropdownOpened: boolean;
        dropdownStatic: boolean;
    };
}

const mapStateToProps = (store: StoreState) => ({
    dropdownOpened: store.navigation.dropdownOpened,
    dropdownStatic: store.navigation.dropdownStatic,
});

export default connect(mapStateToProps)(HomeScreen);