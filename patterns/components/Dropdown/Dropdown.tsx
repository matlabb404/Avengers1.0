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
    // animatedValues: Animated.Value; // Add animatedValue as a required prop
    animatedValues: Animated.Value; // Integer value to reflect the animation progress
    setAnimatedValues: (value: number) => void;
}

const Dropdown: React.FC<DropdownProps> = ({ headers, navigation, animatedValues, setAnimatedValues }) => {
    const touchY = React.useRef<number | null>(null);
    // State to track the active link
    const [activeLink, setActiveLink] = useState<string | null>(null);

    const originalWidthRef = useRef<number | null>(null);

    // Animated value to control the height of the dropdown
    const animatedValue = useRef(new Animated.Value(0)).current;

    // Screen dimensions
    const screenHeight = Dimensions.get("window").height;
    const halfScreenHeight = screenHeight / 2;

    // Gesture handling with PanResponder
    const panResponder = useRef(
        PanResponder.create({
            onStartShouldSetPanResponder: () => true,
            onPanResponderMove: (_, gestureState) => {
                // Dynamically calculate the new position based on gesture
                const newby = Math.sqrt(gestureState.dy * gestureState.dy);

                if (newby > 20) {
                    if (gestureState.dy > 0) {
                        if (animatedValues._value === 0) {
                        console.log("gesture direction", gestureState.dy);
                        const newValue = Math.max(0, Math.min(screenHeight, gestureState.dy));
                        animatedValue.setValue(newValue);
                        console.log(`PanResponder Move down: ${newValue}`);
                        } 
                    } else {
                        if (animatedValues._value != 0) {
                        const newValue = screenHeight + gestureState.dy;
                        animatedValue.setValue(newValue);
                        console.log(`PanResponder Move up: ${newValue}`);
                        }
                    } // Log movement value temp fix
                }
            },
            onPanResponderRelease: (_, gestureState) => {
                // Determine if the dropdown should collapse or expand based on release position
                const releasePoint = gestureState.moveY; // Y position where the touch was released
                const shouldCollapse = releasePoint > halfScreenHeight;

                // Animate the dropdown to its new position
                Animated.timing(animatedValue, {
                    toValue: shouldCollapse ? screenHeight : 0,
                    duration: 200,
                    useNativeDriver: false,
                }).start();

                animatedValues.setValue(shouldCollapse ? screenHeight : 0);

                console.log(
                    `PanResponder Released: Should collapse? ${shouldCollapse}`,
                    'New AnimatedValues:', animatedValues
                );
            },
        })
    ).current;

    // Function to handle header clicks
    function doswipeup() {
        // Use the position listener value from animatedValue listener
        const currentValue = animatedValue._value;
        console.log("Current animated value:", currentValue); // Log current value for debugging

        // Check if current position is greater than 90 (not collapsed)
        if (currentValue > 90) {
            console.log("Animating to collapse...");
            Animated.timing(animatedValue, {
                toValue: 0, // Collapse or scroll up
                duration: 200,
                useNativeDriver: false, // Use native driver for better performance
            }).start();
        } else {
            console.log("Current position is too low to collapse.");
        }
    }

    // Function to handle header clicks
    function doswipedown() {
        // Use the position listener value from animatedValue listener
        const currentValue = animatedValue._value;
        console.log("Current animated value:", currentValue); // Log current value for debugging

        // Check if current position is greater than 90 (not collapsed)
        if (currentValue < 90) {
            console.log("Animating to collapse...");
            Animated.timing(animatedValue, {
                toValue: screenHeight, // Collapse or scroll up
                duration: 200,
                useNativeDriver: false, // Use native driver for better performance
            }).start();
        } else {
            console.log("Current position is too low to collapse.");
        }
    }

    // Function to handle header clicks
    const onPressHandler = (header: ColumnHeader) => {
        console.log(`Header pressed: ${header.value} (link: ${header.link})`);

        // Reset all headers to have isActive = false
        headers.forEach((h: ColumnHeader) => {
            h.isActive = false;
        });

        // Set the clicked header as active
        header.isActive = true;

        // Update the active link and navigate
        setActiveLink(header.link);
        navigation.navigate(header.link);
    };

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
            outputRange: ["20%", "100%"], // Adjust minimum and maximum container width
            extrapolate: "clamp",
        }),
    };

    const dynamicIcon = {
        opacity: animatedValue.interpolate({
            inputRange: [screenHeight / 2, screenHeight / 2 + screenHeight / 4], // Adjust based on screen height
            outputRange: [0, 1],
            extrapolate: "clamp",
        }),
        width: animatedValue.interpolate({
            inputRange: [screenHeight / 2, screenHeight / 2 + screenHeight / 4], // Adjust based on screen height
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
            outputRange: ["100vw", "100vw"],
            extrapolate: "clamp",
        }),
    };

    const dynamictitleBox = {
        opacity: animatedValue.interpolate({
            inputRange: [0, screenHeight / 2],
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

    // BackHandler to collapse the dropdown on back press
    useEffect(() => {
        const backHandler = BackHandler.addEventListener(
            "hardwareBackPress",
            () => {
                console.log("Back button pressed, collapsing dropdown");
                Animated.timing(animatedValue, {
                    toValue: 0,
                    duration: 300,
                    useNativeDriver: false,
                }).start();
                return true; // Prevent default back behavior
            }
        );

        return () => {
            console.log("Removing back handler");
            backHandler.remove(); // Cleanup the event listener on unmount
        };
    }, []);

    return (
        <Animated.View style={[styles.backdrop, dynamicBackdrop]}>
            <Animated.View style={[styles.main, containerDynamicStyle]}>
                <Animated.View
                    style={[styles.TopBox, topBoxStyle]}
                    {...panResponder.panHandlers}
                // onTouchStart={e => touchY.current = e.nativeEvent.pageY}
                // onTouchEnd={e => {
                //     if (touchY.current !== null && touchY.current - e.nativeEvent.pageY > 30) {
                //         {
                //             if (touchY.current !== null && touchY.current - e.nativeEvent.pageY > 40) {//when first is bigger than second it's a swipe up
                //                 doswipeup();
                //                 console.log('a swipe up', touchY.current, e.nativeEvent.pageY)
                //             }
                //         };
                //     }
                //     if (touchY.current !== null && e.nativeEvent.pageY - touchY.current > 30) {
                //         if (touchY.current !== null && e.nativeEvent.pageY - touchY.current > 30) {//when second is bigger than first it's a swipe down
                //             doswipedown();
                //             console.log('a swipe down');
                //         }
                //     }
                // }}
                >
                    <Animated.View
                        style={[styles.headerBox, dynamictitleBox]}
                        onLayout={(event) => {
                            if (!originalWidthRef.current) {
                                originalWidthRef.current = event.nativeEvent.layout.width;
                                console.log("Header box width: ", originalWidthRef.current);
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
            </Animated.View>
        </Animated.View>
    );
};

export default Dropdown;

// // onLayout={(event) => {
//             //     const { height } = event.nativeEvent.layout;

//             //     // Update both state and ref
//             //     settopBoxHeight(height);
//             // }}
//             >
//             <Animated.View style={[styles.TopBox, topBoxStyle]}
//                 {...panResponder.panHandlers}
//                 // onTouchStart={e => touchY.current = e.nativeEvent.pageY}
//                 // onTouchEnd={e => {
//                 //     if (touchY.current !== null && touchY.current - e.nativeEvent.pageY > 30)
//                 //         if (touchY.current !== null && touchY.current - e.nativeEvent.pageY > 30)//when first is bigger than second it's a swipe up
//                 //             //doswipeup(); bugs will fix later
//                 //             console.log('a swipe up')
//                 //     if (touchY.current !== null && e.nativeEvent.pageY - touchY.current > 30)
//                 //         if (touchY.current !== null && e.nativeEvent.pageY - touchY.current > 30)//when second is bigger than first it's a swipe down
//                 //             console.log('a swipe down')
//                 // }}
//             ></Animated.View>
