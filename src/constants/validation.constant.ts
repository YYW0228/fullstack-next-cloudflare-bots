export const VALIDATION_LIMITS = {
    TRADING_BOT: {
        NAME_MIN: 3,
        NAME_MAX: 50,
        DESCRIPTION_MAX: 500,
        POSITION_SIZE_MIN: 1,
        POSITION_SIZE_MAX: 10000,
    },
    UPLOAD: {
        MAX_FILE_SIZE: 5 * 1024 * 1024, // 5MB
        ALLOWED_IMAGE_TYPES: ["image/jpeg", "image/png"],
    },
} as const;

export const VALIDATION_MESSAGES = {
    REQUIRED: "This field is required",
    EMAIL_INVALID: "Please enter a valid email address",
    PASSWORD_TOO_SHORT: "Password must be at least 8 characters",
    USERNAME_TOO_SHORT: "Username must be at least 3 characters",
    FILE_TOO_LARGE: "File size must be less than 5MB",
    INVALID_FILE_TYPE: "Only JPEG and PNG files are allowed",
} as const;

export const TRADING_BOT_VALIDATION_MESSAGES = {
    NAME_REQUIRED: "Bot name is required",
    NAME_TOO_LONG: "Bot name must be less than 50 characters",
    DESCRIPTION_TOO_LONG: "Description must be less than 500 characters",
    INVALID_POSITION_SIZE: "Position size must be between 1 and 10000",
    STRATEGY_TYPE_REQUIRED: "Strategy type is required",
} as const;
