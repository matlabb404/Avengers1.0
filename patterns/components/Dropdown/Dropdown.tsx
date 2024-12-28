import React, { useEffect, useRef, useState } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    Animated,
    PanResponder,
    Dimensions,
    BackHandler,
} from "react-native";
import styles from "./dropdown.style";

// Define the type for the column headers
interface ColumnHeader {
    link: string;
    value: string;
    isActive: boolean;
}

// Props for the Dropdown component
interface DropdownProps {
    headers: ColumnHeader[];
    navigation: any; // Navigation object for screen navigation
}

const Dropdown: React.FC<DropdownProps> = ({ headers, navigation }) => {
    const [activeLink, setActiveLink] = useState<string | null>(null);
    const [originalWidth, setOriginalWidth] = useState<number | null>(null); // Track the original width
    const originalWidthRef = useRef<number | null>(null);
    const touchY = React.useRef<number | null>(null);
    let topBoxHeight = 0;
    function settopBoxHeight(num: number) {
        topBoxHeight = num;
    };

    function gettopBoxHeight() {
        return topBoxHeight;
    };
    const animatedValue = useRef(new Animated.Value(gettopBoxHeight())).current;
    // const touchY = React.useRef<number | null>(null);

    const screenHeight = Dimensions.get("window").height;
    const halfScreenHeight = screenHeight / 2;

    // Log the current position of the TopBox (even without a gesture)

    const positionListener = animatedValue.addListener(({ value }) => { value });
    const heightListener = useRef(new Animated.Value(screenHeight)).current;

    const panResponder = useRef(
        PanResponder.create({
            onStartShouldSetPanResponder: () => true,
            onPanResponderMove: (_, gestureState) => {
                let newdy;
                if (gestureState.dy > 5) {
                    newdy = gestureState.dy;
                } else if (gestureState.dy < -5) {
                    newdy = gestureState.dy;
                } else {
                    newdy = 0;
                }
                let newValue;
                if (gettopBoxHeight() < 90) {
                    newValue = Math.max(0, Math.min(newdy, screenHeight));
                } else {
                    newValue = screenHeight + gestureState.dy;
                }

                animatedValue.setValue(newValue);
            },
            onPanResponderRelease: (_, gestureState) => {
                {
                    const releasePoint = gestureState.moveY; // Y position where the touch was released
                    const shouldCollapse = releasePoint > halfScreenHeight;
                    if (!shouldCollapse) { settopBoxHeight(0); } else { settopBoxHeight(screenHeight); }
                    // Animate based on release position
                    Animated.timing(animatedValue, {
                        toValue: shouldCollapse ? screenHeight : 0, // Collapse or scroll up
                        duration: 100,
                        useNativeDriver: false,
                    }).start();
                }
            },
        })
    ).current;

    function doswipeup() {
        // Check if current position is not already at 0 (collapsed)
        if (gettopBoxHeight() > 80) {
            Animated.timing(animatedValue, {
                toValue: 0, // Collapse or scroll up
                duration: 300,
                useNativeDriver: false, // Use native driver for better performance (set to true if your view supports it)
            }).start();
        }
    }


    const containerDynamicStyle = {
        height: animatedValue.interpolate({
            inputRange: [0, screenHeight], // Adjust based on screen height
            outputRange: [80, screenHeight - 80], // Adjust minimum and maximum container height
            extrapolate: "clamp",
        }),
    };

    const dynamicIconBox = {
        width: animatedValue.interpolate({
            inputRange: [0, screenHeight], // Adjust based on screen height
            outputRange: ['20%', '100%'], // Adjust minimum and maximum container width
            extrapolate: "clamp",
        }),
    };
    
    const dynamicIcon = {
            opacity: animatedValue.interpolate({
                inputRange: [screenHeight/2, (screenHeight/2+ screenHeight/4)], // Adjust based on screen height
                outputRange: [0, 1],
                extrapolate: "clamp",
            }),
            width: animatedValue.interpolate({
                inputRange: [screenHeight/2, (screenHeight/2+ screenHeight/4)], // Adjust based on screen height
                outputRange: [0, 70], // Adjust minimum and maximum container width
                extrapolate: "clamp",
            }),
        };

    const dynamicBackdrop = {
            height: animatedValue.interpolate({
                inputRange: [0, screenHeight],
                outputRange: [70, screenHeight],
                extrapolate: "clamp",
            }),
            width: animatedValue.interpolate({
                inputRange: [0, screenHeight],
                outputRange: ['100vw', '100vw'],
                extrapolate: "clamp",
            })
        };

    const dynamictitleBox = {
            opacity: animatedValue.interpolate({
                inputRange: [0, screenHeight/2],
                outputRange: [1, 0],
                extrapolate: "clamp",
            }),
            marginLeft: animatedValue.interpolate({
                inputRange: [0, screenHeight],
                outputRange: [0, -2000],
                extrapolate: "clamp",
            }),
        };

    const topBoxStyle = {
        transform: [
            {
                translateY: animatedValue.interpolate({
                    inputRange: [0, screenHeight], // Adjust based on screen height
                    outputRange: [0, screenHeight - 100], // Adjust minimum and maximum container height
                    extrapolate: "clamp", // Prevent the value from going beyond bounds
                }),
            },
        ],
    };

    const onPressHandler = (header: any) => {
        // Reset all headers to have isActive = false
        headers.forEach((h: any) => {
            h.isActive = false;
        });

        // Set the clicked header as active
        header.isActive = true;

        // Update the active link and navigate
        setActiveLink(header.link);
        navigation.navigate(header.link);
    };

    useEffect(() => {
        const backHandler = BackHandler.addEventListener("hardwareBackPress", () => {
            Animated.timing(animatedValue, {
                toValue: 0,
                duration: 300,
                useNativeDriver: false,
            }).start();
            settopBoxHeight(0);
            return true; // Prevent default back behavior
        });
        return () => {
            // Remove the back handler backHandler.remove();
    
            // Reset animation
        };
    }, []);
    

    return (
        <Animated.View style={[styles.backdrop, dynamicBackdrop]}>
        <Animated.View
        style={[styles.main, containerDynamicStyle]}
        // onLayout={(event) => {
            //     const { height } = event.nativeEvent.layout;
            
            //     // Update both state and ref
            //     settopBoxHeight(height);
            // }}
            >
            <Animated.View style={[styles.TopBox, topBoxStyle]}
                {...panResponder.panHandlers}
                // onTouchStart={e => touchY.current = e.nativeEvent.pageY}
                // onTouchEnd={e => {
                //     if (touchY.current !== null && touchY.current - e.nativeEvent.pageY > 30)
                //         if (touchY.current !== null && touchY.current - e.nativeEvent.pageY > 30)//when first is bigger than second it's a swipe up
                //             //doswipeup(); bugs will fix later
                //             console.log('a swipe up')
                //     if (touchY.current !== null && e.nativeEvent.pageY - touchY.current > 30)
                //         if (touchY.current !== null && e.nativeEvent.pageY - touchY.current > 30)//when second is bigger than first it's a swipe down
                //             console.log('a swipe down')
                // }}
            >
                <Animated.View style={[styles.headerBox, dynamictitleBox]}
                    onLayout={(event) => {
                        if (!originalWidthRef.current) {
                            originalWidthRef.current = event.nativeEvent.layout.width;
                        }
                    }}
            >
                {headers.map((header, index) => (
                    <TouchableOpacity
                        key={index}
                        style={[
                            styles.headerContainer,
                            header.isActive && styles.activeButton, // Apply activeButton style if link is active
                        ]}
                        onPress={() => onPressHandler(header)}
                    >
                        <Text style={styles.headerText}>{header.value}</Text>
                    </TouchableOpacity>
                ))}
            </Animated.View>
            <Animated.View style={[styles.iconBox, dynamicIconBox]}>
                <Text>Notification</Text>
                <Animated.Text style={[dynamicIcon]}>Saved</Animated.Text>
                <Animated.Text style={[dynamicIcon]}>Bookings</Animated.Text>
                <Text>Chat</Text>
            </Animated.View>
        </Animated.View>
        </Animated.View >
        </Animated.View>
    );
};

export default Dropdown;
