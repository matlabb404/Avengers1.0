import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
    main: {
        margin: 0,
        padding: 0,
        width: '100%',
        borderBottomWidth: 4,
        borderBottomLeftRadius: theme.sizes.xxsmall,
        borderBottomRightRadius: theme.sizes.xxsmall,
        backgroundColor: theme.colors.primary,
    },
    TopBox: {
        flexDirection: 'row',
        padding: 0,
        height: 50,
        maxHeight: 50,
        marginTop: 25,
        width: '90%',
        marginLeft: '5%',
        marginRight: '5%',
        // justifyContent: 'space-between',
        overflowX: 'hidden',
        overflowY: 'clip',
    },
    iconBox: { 
        minWidth: 145,
        flexDirection: 'row', 
        paddingLeft: 30,
        gap: '20%',
        // justifyContent: 'space-between',
    },
    headerBox: {
        flexDirection: 'row',
        backgroundColor: theme.colors.secondary,
        height: theme.sizes.xxlarge,
        padding:0,
        marginTop: 5,
        marginLeft: 5,
        justifyContent: 'center',
        borderRadius: theme.sizes.xxsmall,
        borderWidth: 2,
        borderColor: theme.colors.secondary,
    },
    headerText: {
        fontSize: theme.sizes.medium,
        fontWeight: 600,
    },
    headerContainer: {
        paddingLeft: theme.sizes.xsmall,
        paddingRight: theme.sizes.xsmall,
        justifyContent: 'center',
    },
    activeButton: {
        paddingRight: theme.sizes.xsmall,
        paddingLeft: theme.sizes.xsmall,
        justifyContent: 'center',
        backgroundColor: theme.colors.primary,
        borderRadius: theme.sizes.xxxsmall,
    },
    backdrop: {
        backgroundColor: theme.colors.highlight,
        zIndex: -5,
        position: 'absolute',
        borderBottomColor: theme.colors.shadowM,
        borderBottomLeftRadius: theme.sizes.xsmall,
        borderBottomRightRadius: theme.sizes.xsmall,
    },
    dropdownpage: {
        top: 200,
        position: 'absolute',
        borderColor: 'yellow',
        borderWidth: 1,
    },
    bottomIconBox: {
        zIndex: -5,
        backgroundColor: theme.colors.highlight,
    },
    activeIcon: {
        backgroundColor: theme.colors.primary,
        borderBottomLeftRadius: theme.sizes.large,
        borderBottomRightRadius: theme.sizes.large,
    }
});

export default styles;