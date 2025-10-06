#!/usr/bin/env tsx

/**
 * 环境检查脚本
 * 自动验证环境配置、依赖和系统状态
 */

import { execSync } from 'child_process';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';
import { validateEnvironment, DeploymentChecker } from '../src/lib/config-validator';

// 颜色输出
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    white: '\x1b[37m'
};

function colorLog(message: string, color: keyof typeof colors = 'white') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSuccess(message: string) {
    colorLog(`✅ ${message}`, 'green');
}

function logError(message: string) {
    colorLog(`❌ ${message}`, 'red');
}

function logWarning(message: string) {
    colorLog(`⚠️  ${message}`, 'yellow');
}

function logInfo(message: string) {
    colorLog(`ℹ️  ${message}`, 'blue');
}

function logSection(title: string) {
    console.log();
    colorLog(`🔍 ${title}`, 'cyan');
    colorLog('='.repeat(50), 'cyan');
}

interface CheckResult {
    name: string;
    status: 'pass' | 'fail' | 'warning';
    message: string;
    details?: any;
}

class EnvironmentChecker {
    private results: CheckResult[] = [];

    async runAllChecks(): Promise<boolean> {
        logSection('环境检查开始');

        const checks = [
            () => this.checkNodeVersion(),
            () => this.checkPackageManager(),
            () => this.checkProjectStructure(),
            () => this.checkDependencies(),
            () => this.checkEnvironmentVariables(),
            () => this.checkConfigFiles(),
            () => this.checkCloudflareTools(),
            () => this.checkBuildStatus(),
            () => this.checkDatabaseSchema(),
            () => this.checkAPIConnectivity()
        ];

        for (const check of checks) {
            try {
                await check();
            } catch (error) {
                this.addResult({
                    name: 'Unknown Check',
                    status: 'fail',
                    message: error instanceof Error ? error.message : String(error)
                });
            }
        }

        this.showSummary();
        return this.isOverallSuccess();
    }

    private checkNodeVersion() {
        logSection('Node.js 版本检查');
        
        try {
            const nodeVersion = process.version;
            const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
            
            if (majorVersion >= 18) {
                logSuccess(`Node.js 版本: ${nodeVersion}`);
                this.addResult({
                    name: 'Node.js Version',
                    status: 'pass',
                    message: `Version ${nodeVersion} is supported`
                });
            } else {
                logError(`Node.js 版本过低: ${nodeVersion} (需要 >= 18.0.0)`);
                this.addResult({
                    name: 'Node.js Version',
                    status: 'fail',
                    message: `Version ${nodeVersion} is too old, requires >= 18.0.0`
                });
            }
        } catch (error) {
            logError('无法检查 Node.js 版本');
            this.addResult({
                name: 'Node.js Version',
                status: 'fail',
                message: 'Failed to check Node.js version'
            });
        }
    }

    private checkPackageManager() {
        logSection('包管理器检查');
        
        try {
            // 检查 pnpm
            const pnpmVersion = execSync('pnpm --version', { encoding: 'utf8' }).trim();
            logSuccess(`pnpm 版本: ${pnpmVersion}`);
            
            // 检查 lockfile
            if (existsSync('pnpm-lock.yaml')) {
                logSuccess('pnpm-lock.yaml 存在');
            } else {
                logWarning('pnpm-lock.yaml 不存在，可能需要重新安装依赖');
            }
            
            this.addResult({
                name: 'Package Manager',
                status: 'pass',
                message: `pnpm ${pnpmVersion} is available`
            });
        } catch (error) {
            logError('pnpm 未安装或不可用');
            this.addResult({
                name: 'Package Manager',
                status: 'fail',
                message: 'pnpm is not available'
            });
        }
    }

    private checkProjectStructure() {
        logSection('项目结构检查');
        
        const requiredFiles = [
            'package.json',
            'next.config.ts',
            'tsconfig.json',
            'src/app',
            'src/workers',
            'src/db',
            'wrangler.trading-bot.toml'
        ];

        let allExists = true;
        for (const file of requiredFiles) {
            if (existsSync(file)) {
                logSuccess(`${file} ✓`);
            } else {
                logError(`${file} ✗`);
                allExists = false;
            }
        }

        this.addResult({
            name: 'Project Structure',
            status: allExists ? 'pass' : 'fail',
            message: allExists ? 'All required files exist' : 'Missing required files'
        });
    }

    private checkDependencies() {
        logSection('依赖检查');
        
        try {
            if (!existsSync('node_modules')) {
                logError('node_modules 不存在，需要安装依赖');
                this.addResult({
                    name: 'Dependencies',
                    status: 'fail',
                    message: 'node_modules not found, run: pnpm install'
                });
                return;
            }

            // 读取 package.json 检查关键依赖
            const packageJson = JSON.parse(readFileSync('package.json', 'utf8'));
            const criticalDeps = [
                'next',
                'react',
                '@cloudflare/next-on-pages',
                'drizzle-orm',
                'better-auth'
            ];

            const missingDeps = criticalDeps.filter(dep => 
                !packageJson.dependencies?.[dep] && !packageJson.devDependencies?.[dep]
            );

            if (missingDeps.length === 0) {
                logSuccess('所有关键依赖都已配置');
                this.addResult({
                    name: 'Dependencies',
                    status: 'pass',
                    message: 'All critical dependencies are configured'
                });
            } else {
                logWarning(`缺少依赖: ${missingDeps.join(', ')}`);
                this.addResult({
                    name: 'Dependencies',
                    status: 'warning',
                    message: `Missing dependencies: ${missingDeps.join(', ')}`
                });
            }
        } catch (error) {
            logError('依赖检查失败');
            this.addResult({
                name: 'Dependencies',
                status: 'fail',
                message: 'Failed to check dependencies'
            });
        }
    }

    private checkEnvironmentVariables() {
        logSection('环境变量检查');
        
        // 检查 .env 文件
        if (!existsSync('.env')) {
            logWarning('.env 文件不存在');
            if (existsSync('.env.example')) {
                logInfo('发现 .env.example，可以复制为 .env');
            }
        }

        // 验证环境变量
        const validation = validateEnvironment();
        if (validation.success) {
            logSuccess('环境变量配置正确');
            this.addResult({
                name: 'Environment Variables',
                status: 'pass',
                message: 'All required environment variables are set'
            });
        } else {
            logError('环境变量配置错误:');
            validation.errors?.forEach(error => logError(`  ${error}`));
            this.addResult({
                name: 'Environment Variables',
                status: 'fail',
                message: 'Environment variables validation failed',
                details: validation.errors
            });
        }
    }

    private checkConfigFiles() {
        logSection('配置文件检查');
        
        const configFiles = [
            {
                file: 'wrangler.trading-bot.toml',
                description: 'Cloudflare Worker 配置'
            },
            {
                file: 'next.config.ts',
                description: 'Next.js 配置'
            },
            {
                file: 'drizzle.config.ts',
                description: 'Drizzle ORM 配置'
            }
        ];

        let allValid = true;
        for (const { file, description } of configFiles) {
            if (existsSync(file)) {
                logSuccess(`${description}: ${file} ✓`);
            } else {
                logError(`${description}: ${file} ✗`);
                allValid = false;
            }
        }

        this.addResult({
            name: 'Configuration Files',
            status: allValid ? 'pass' : 'fail',
            message: allValid ? 'All configuration files exist' : 'Missing configuration files'
        });
    }

    private checkCloudflareTools() {
        logSection('Cloudflare 工具检查');
        
        try {
            // 检查 wrangler
            const wranglerVersion = execSync('npx wrangler --version', { encoding: 'utf8' }).trim();
            logSuccess(`Wrangler: ${wranglerVersion}`);

            // 检查认证状态
            try {
                execSync('npx wrangler whoami', { stdio: 'pipe' });
                logSuccess('Wrangler 已认证');
                this.addResult({
                    name: 'Cloudflare Tools',
                    status: 'pass',
                    message: 'Wrangler is installed and authenticated'
                });
            } catch {
                logWarning('Wrangler 未认证，运行: npx wrangler login');
                this.addResult({
                    name: 'Cloudflare Tools',
                    status: 'warning',
                    message: 'Wrangler not authenticated, run: npx wrangler login'
                });
            }
        } catch (error) {
            logError('Wrangler 不可用');
            this.addResult({
                name: 'Cloudflare Tools',
                status: 'fail',
                message: 'Wrangler is not available'
            });
        }
    }

    private async checkBuildStatus() {
        logSection('构建状态检查');
        
        try {
            logInfo('运行类型检查...');
            execSync('pnpm run type-check', { stdio: 'pipe' });
            logSuccess('TypeScript 类型检查通过');

            logInfo('测试构建...');
            execSync('pnpm run build', { stdio: 'pipe' });
            logSuccess('项目构建成功');

            this.addResult({
                name: 'Build Status',
                status: 'pass',
                message: 'Project builds successfully'
            });
        } catch (error) {
            logError('构建失败');
            this.addResult({
                name: 'Build Status',
                status: 'fail',
                message: 'Build failed',
                details: error instanceof Error ? error.message : String(error)
            });
        }
    }

    private checkDatabaseSchema() {
        logSection('数据库模式检查');
        
        const migrationFile = 'src/drizzle/0000_initial_schemas_migration.sql';
        if (existsSync(migrationFile)) {
            logSuccess('数据库迁移文件存在');
            this.addResult({
                name: 'Database Schema',
                status: 'pass',
                message: 'Database migration file exists'
            });
        } else {
            logWarning('数据库迁移文件不存在，可能需要生成');
            this.addResult({
                name: 'Database Schema',
                status: 'warning',
                message: 'Database migration file not found'
            });
        }
    }

    private async checkAPIConnectivity() {
        logSection('API 连接检查');
        
        // 这里可以添加 OKX API 连接测试
        // 为了安全起见，我们只检查配置是否存在
        const requiredVars = ['OKX_API_KEY', 'OKX_SECRET', 'OKX_PASSPHRASE'];
        const hasApiConfig = requiredVars.every(varName => process.env[varName]);
        
        if (hasApiConfig) {
            logSuccess('API 配置存在（未测试连接以保护安全）');
            this.addResult({
                name: 'API Connectivity',
                status: 'pass',
                message: 'API credentials are configured'
            });
        } else {
            logWarning('API 配置不完整');
            this.addResult({
                name: 'API Connectivity',
                status: 'warning',
                message: 'API credentials not fully configured'
            });
        }
    }

    private addResult(result: CheckResult) {
        this.results.push(result);
    }

    private showSummary() {
        logSection('检查结果摘要');
        
        const passCount = this.results.filter(r => r.status === 'pass').length;
        const failCount = this.results.filter(r => r.status === 'fail').length;
        const warningCount = this.results.filter(r => r.status === 'warning').length;
        
        console.log();
        colorLog(`总检查项: ${this.results.length}`, 'white');
        colorLog(`✅ 通过: ${passCount}`, 'green');
        colorLog(`❌ 失败: ${failCount}`, 'red');
        colorLog(`⚠️  警告: ${warningCount}`, 'yellow');
        
        if (failCount > 0) {
            console.log();
            colorLog('失败的检查项:', 'red');
            this.results
                .filter(r => r.status === 'fail')
                .forEach(r => logError(`${r.name}: ${r.message}`));
        }
        
        if (warningCount > 0) {
            console.log();
            colorLog('警告的检查项:', 'yellow');
            this.results
                .filter(r => r.status === 'warning')
                .forEach(r => logWarning(`${r.name}: ${r.message}`));
        }
        
        console.log();
        if (this.isOverallSuccess()) {
            logSuccess('🎉 环境检查完成，可以进行部署！');
        } else {
            logError('💥 环境检查失败，请修复上述问题后重试');
        }
    }

    private isOverallSuccess(): boolean {
        return this.results.filter(r => r.status === 'fail').length === 0;
    }
}

// 主程序
async function main() {
    console.log();
    colorLog('🤖 反向跟单机器人环境检查', 'magenta');
    colorLog('=====================================', 'magenta');
    
    const checker = new EnvironmentChecker();
    const success = await checker.runAllChecks();
    
    process.exit(success ? 0 : 1);
}

// 运行检查
if (require.main === module) {
    main().catch(error => {
        logError(`检查过程中发生错误: ${error.message}`);
        process.exit(1);
    });
}