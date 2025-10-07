CREATE TABLE `simple_positions` (
	`id` text PRIMARY KEY NOT NULL,
	`strategy_instance_id` text,
	`side` text NOT NULL,
	`size` real NOT NULL,
	`entry_price` real NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`order_id` text NOT NULL,
	`opened_at` integer NOT NULL,
	`closed_at` integer,
	`pnl` real,
	`close_reason` text,
	FOREIGN KEY (`strategy_instance_id`) REFERENCES `strategy_instances`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `strategy_instances` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`name` text NOT NULL,
	`market_pair` text NOT NULL,
	`strategy_type` text NOT NULL,
	`status` text DEFAULT 'stopped' NOT NULL,
	`config` text NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `turtle_positions` (
	`id` text PRIMARY KEY NOT NULL,
	`sequence_id` text,
	`side` text NOT NULL,
	`size` real NOT NULL,
	`entry_price` real NOT NULL,
	`signal_quantity` integer NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`order_id` text NOT NULL,
	`opened_at` integer NOT NULL,
	FOREIGN KEY (`sequence_id`) REFERENCES `turtle_sequences`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `turtle_sequences` (
	`id` text PRIMARY KEY NOT NULL,
	`strategy_instance_id` text,
	`direction` text NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`current_max_quantity` integer DEFAULT 0 NOT NULL,
	`started_at` integer NOT NULL,
	`closed_at` integer,
	FOREIGN KEY (`strategy_instance_id`) REFERENCES `strategy_instances`(`id`) ON UPDATE no action ON DELETE cascade
);
