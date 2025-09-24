# Security Module for Qwen Code

The security module provides comprehensive security measures for the Qwen Code CLI application, implementing best practices for input validation, credential management, rate limiting, and audit logging.

## Components

### 1. Input Validation and Sanitization

The `validation.py` module provides:

- **InputValidator**: Validates filenames, paths, URLs, API keys, and sanitizes input to prevent injection attacks
- **PathSecurity**: Prevents path traversal attacks
- **DataSanitizer**: Sanitizes environment variables and masks sensitive data

Key security features:
- SQL injection prevention
- XSS prevention
- Path traversal prevention
- Command injection detection
- API key format validation

### 2. Secure Credential Management

The `credentials.py` module provides:

- **SecureCredentials**: Enhanced credentials data structure with expiration tracking
- **SecureCredentialManager**: Secure storage using scrypt-based key derivation and Fernet encryption
- Per-credential salting for additional security
- Credential rotation capability

Key security features:
- Scrypt-based key derivation (more secure than PBKDF2)
- Per-credential salting
- Encrypted storage in SQLite database
- Credential expiration tracking
- Access counting and audit trail

### 3. API Rate Limiting

The `rate_limiting.py` module provides:

- **RateLimiter**: Sliding window algorithm for rate limiting
- **APIRateLimiter**: Pre-configured rate limits for different API endpoints
- Configurable limits per user, IP, or API key

Default rate limits:
- Chat API: 60 requests per minute per user
- Auth API: 10 requests per minute per IP (more restrictive)
- File operations: 100 operations per minute per user
- Token refresh: 5 attempts per minute per user

### 4. Audit Logging

The `audit.py` module provides:

- **AuditLogger**: Structured logging for security events
- **SecurityEventType**: Enum for different security event types
- **SecurityMonitor**: Integration point for monitoring and alerting

Logged events include:
- Authentication success/failure
- Authorization failures
- Input validation failures
- Rate limit exceeded
- Unauthorized access attempts
- Suspicious activity
- Credential access/changes
- Configuration changes
- File access
- API calls
- Session creation/destruction

## Implementation Details

### Security in CLI Commands

The enhanced `commands.py` implements:

- Input validation for all user inputs
- Rate limiting for API endpoints
- Sanitization of user messages
- Command injection prevention
- Secure credential handling
- Audit logging for security-relevant events

### Security Initialization

The `init.py` module ensures all security features are properly initialized when the application starts.

## Security Configuration

### Environment Variables

- `QWEN_CREDENTIAL_PASSWORD`: Password for encrypting credentials (required for production)
- `QWEN_LOG_LEVEL`: Logging level (default: INFO)
- `QWEN_LOG_FILE`: Optional file to write logs to

### Credential Encryption

Credentials are encrypted using:
1. A scrypt-derived key from `QWEN_CREDENTIAL_PASSWORD` environment variable
2. A randomly generated salt stored securely in the database
3. Per-credential additional salting
4. Fernet (AES 128 CFB) encryption

## Threat Mitigation

This security implementation addresses:

1. **Injection Attacks**: Input validation and sanitization
2. **Credential Theft**: Encrypted storage with strong key derivation
3. **Rate Limiting**: Brute force and DoS protection
4. **Path Traversal**: Secure path validation
5. **Information Disclosure**: Proper logging and data masking
6. **Authentication Bypass**: Secure authentication flow
7. **Session Hijacking**: Secure session handling (pending implementation)

## Compliance

The security implementation follows best practices for:
- OWASP Top 10
- NIST Cybersecurity Framework
- SOC2 Type II requirements
- GDPR data protection principles