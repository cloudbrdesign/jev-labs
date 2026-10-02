"""Values every lab shares."""

# The versioned model ID the labs pin. Aliases such as `jev-latest` move when TypeSafe
# ships a new release; the versioned ID does not. Update this only after a new recorded run.
MODEL = "jev-1.13.0"

# The SDK version the labs were written and recorded with (see requirements.txt).
SDK_PIN = "0.7.2"

# Replay and offline modes need a non-empty key string because the SDK refuses to start
# without one. It is never sent anywhere: those modes never open a network connection.
PLACEHOLDER_KEY = "not-a-real-key-no-network"
