"use client";

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { PlusCircle } from 'lucide-react';

// Simple form schema that works with string inputs
const formSchema = z.object({
    name: z.string().min(3, 'Instance name must be at least 3 characters'),
    marketPair: z.string().min(1, 'Market pair is required'),
    strategyType: z.enum(['simple-reverse', 'turtle-reverse']),
    profitTarget: z.string().min(1, 'Required'),
    stopLoss: z.string().min(1, 'Required'),
    positionTimeoutHours: z.string().min(1, 'Required'),
});

type FormValues = z.infer<typeof formSchema>;

export function CreateBotDialog() {
    const [open, setOpen] = useState(false);

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button>
                    <PlusCircle className="w-4 h-4 mr-2" />
                    Create Bot
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Create New Strategy Instance</DialogTitle>
                    <DialogDescription>
                        Configure and launch a new trading bot.
                    </DialogDescription>
                </DialogHeader>
                <BotForm onSuccess={() => setOpen(false)} />
            </DialogContent>
        </Dialog>
    );
}

function BotForm({ onSuccess }: { onSuccess: () => void }) {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);
    
    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: '',
            marketPair: 'BTC-USDT-SWAP',
            strategyType: 'simple-reverse',
            profitTarget: '0.3',
            stopLoss: '-0.15',
            positionTimeoutHours: '6',
        },
    });

    async function onSubmit(values: FormValues) {
        setIsSubmitting(true);
        try {
            // Convert string values to appropriate types for API
            const payload = {
                name: values.name,
                marketPair: values.marketPair,
                strategyType: values.strategyType,
                config: values.strategyType === 'simple-reverse' ? {
                    basePositionSize: 10,
                    maxPositionSize: 100,
                    profitTarget: parseFloat(values.profitTarget),
                    stopLoss: parseFloat(values.stopLoss),
                    positionTimeoutHours: parseInt(values.positionTimeoutHours),
                    maxConcurrentPositions: 5,
                } : {
                    positionSizes: { 1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80 },
                    profitThresholds: { 1: 0.0, 2: 0.0, 3: 0.50, 4: 0.30, 5: 0.30, 6: 0.30, 7: 0.30, 8: 0.30 },
                    closeRatios: { 1: 0.0, 2: 0.0, 3: 0.50, 4: 0.80, 5: 0.90, 6: 0.90, 7: 0.90, 8: 1.00 },
                    emergencyStopLoss: parseFloat(values.stopLoss),
                    sequenceTimeoutHours: parseInt(values.positionTimeoutHours),
                    maxPositionSize: 1000,
                },
            };

            const response = await fetch('/api/trading-bots', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const result = await response.json() as { error?: string };

            if (!response.ok) {
                throw new Error(result.error || 'Failed to create instance');
            }

            toast.success('Strategy instance created successfully!');
            router.refresh();
            onSuccess();

        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'An unknown error occurred');
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Instance Name</FormLabel>
                            <FormControl>
                                <Input placeholder="My BTC Bot" {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="marketPair"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Market Pair</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select market pair" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    <SelectItem value="BTC-USDT-SWAP">BTC-USDT-SWAP</SelectItem>
                                    <SelectItem value="ETH-USDT-SWAP">ETH-USDT-SWAP</SelectItem>
                                    <SelectItem value="SOL-USDT-SWAP">SOL-USDT-SWAP</SelectItem>
                                </SelectContent>
                            </Select>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="strategyType"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Strategy Type</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select strategy" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    <SelectItem value="simple-reverse">Simple Reverse</SelectItem>
                                    <SelectItem value="turtle-reverse">Turtle Reverse</SelectItem>
                                </SelectContent>
                            </Select>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Configuration</h3>
                    
                    <FormField
                        control={form.control}
                        name="profitTarget"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Profit Target</FormLabel>
                                <FormControl>
                                    <Input placeholder="0.3" {...field} />
                                </FormControl>
                                <FormDescription>e.g., 0.3 for 30%</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="stopLoss"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Stop Loss</FormLabel>
                                <FormControl>
                                    <Input placeholder="-0.15" {...field} />
                                </FormControl>
                                <FormDescription>e.g., -0.15 for -15%</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="positionTimeoutHours"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Position Timeout (Hours)</FormLabel>
                                <FormControl>
                                    <Input placeholder="6" {...field} />
                                </FormControl>
                                <FormDescription>Auto-close after this many hours</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <Button type="submit" disabled={isSubmitting} className="w-full">
                    {isSubmitting ? 'Creating...' : 'Create Bot'}
                </Button>
            </form>
        </Form>
    );
}