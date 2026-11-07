import { useEffect, useMemo, useState } from "react";
import { Animated, Modal, Pressable, useWindowDimensions, View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { WorkspaceThreadSidebar } from "../layout/workspace/WorkspaceThreadSidebar";

/**
 * Crook-style sidebar for compact screens: the same thread tree as the workspace
 * sidebar, slid over the chat. Open from the chat's left edge; close by swiping
 * the drawer left, tapping the scrim, or selecting a thread.
 */
export function CompactSidebarDrawer(props: {
  readonly visible: boolean;
  readonly onClose: () => void;
}) {
  const { visible, onClose } = props;
  const { width: windowWidth } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const drawerWidth = Math.min(340, Math.round(windowWidth * 0.76));
  const [translateX] = useState(() => new Animated.Value(-drawerWidth));

  // oxlint-disable-next-line t3code/no-unreasoned-state-sync -- keeps the native drawer offset in step with the visible prop
  useEffect(() => {
    if (!visible) return;
    translateX.setValue(-drawerWidth);
    Animated.timing(translateX, {
      toValue: 0,
      duration: 220,
      useNativeDriver: false,
    }).start();
  }, [drawerWidth, translateX, visible]);

  const closeGesture = useMemo(
    () =>
      // oxlint-disable-next-line react/capitalized-calls -- Gesture.Pan is a gesture factory, not a React component.
      Gesture.Pan()
        .runOnJS(true)
        .activeOffsetX([-16, 16])
        .failOffsetY([-18, 18])
        .onUpdate((event) => {
          if (event.translationX < 0) {
            translateX.setValue(event.translationX);
          }
        })
        .onEnd((event) => {
          if (event.translationX < -drawerWidth * 0.22 || event.velocityX < -600) {
            onClose();
            return;
          }
          Animated.spring(translateX, {
            toValue: 0,
            bounciness: 0,
            useNativeDriver: false,
          }).start();
        }),
    [drawerWidth, onClose, translateX],
  );

  return (
    <Modal
      animationType="none"
      navigationBarTranslucent
      onRequestClose={onClose}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View className="flex-1 flex-row">
        <GestureDetector gesture={closeGesture}>
          <Animated.View
            className="h-full bg-drawer"
            style={{ width: drawerWidth, transform: [{ translateX }] }}
          >
            <View className="flex-1" style={{ paddingTop: insets.top }}>
              <WorkspaceThreadSidebar
                onRequestVisibility={() => undefined}
                onWillNavigate={onClose}
                visible
                width={drawerWidth}
              />
            </View>
          </Animated.View>
        </GestureDetector>
        <Pressable
          accessibilityLabel="Close sidebar"
          accessibilityRole="button"
          className="flex-1"
          onPress={onClose}
          style={{ backgroundColor: "rgba(0,0,0,0.28)" }}
        />
      </View>
    </Modal>
  );
}
