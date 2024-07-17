
# Database Access Documentation

## Overview
This document provides information on how to connect to the MySQL database hosted on Amazon RDS.

## Connecting to the MySQL Database

### Prerequisites
- Amazon RDS instance with MySQL
- Security group settings that allow access from your EC2 instance or local machine
- MySQL client

### Connection Details
- **RDS Endpoint**: `database-1.cbguawgeickp.us-east-2.rds.amazonaws.com`
- **Port**: `3306`
- **Database Name**: `user_preferences_db`
- **Username**: `garytayl`
- **Password**: Your master password

### Using MySQL Client

1. **Install MySQL Client**:
   ```sh
   sudo yum install -y mysql
   ```

2. **Connect to the RDS Instance**:
   ```sh
   docker run -it --rm mysql:latest mysql -h database-1.cbguawgeickp.us-east-2.rds.amazonaws.com -u garytayl -p
   ```
   - Enter your master password when prompted.
   
   - Then switch to the Database:
   
         ```sql
         USE user_preferences_db;
         ```

### Using Docker to Run MySQL Client

1. **Install Docker**:
   ```sh
   sudo yum update -y
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```

2. **Pull the MySQL Docker Image**:
   ```sh
   docker pull mysql:latest
   ```

3. **Run the MySQL Client in Docker**:
   ```sh
   docker run -it --rm mysql:latest mysql -h database-1.cbguawgeickp.us-east-2.rds.amazonaws.com -u garytayl -p
   ```

   
      | Column Name       | Data Type      | Description                           |
      |-------------------|----------------|---------------------------------------|
      | `user_id`         | VARCHAR(255)   | Primary key, unique user identifier   |
      | `api_key`         | TEXT           | User's ElevenLabs API key             |
      | `voices`          | TEXT           | JSON string of user's voice settings  |
      | `current_voice_id`| VARCHAR(255)   | ID of the currently selected voice    |



## Additional Notes
- Ensure your RDS instance is properly secured and accessible only from trusted IP addresses.
- Regularly back up your database to prevent data loss.


## Database Query Examples

Here are some useful queries to check the database:

### Show Databases
```sql
SHOW DATABASES;
```

### Use Database
```sql
USE user_preferences_db;
```

### Show Tables
```sql
SHOW TABLES;
```

### Describe Table
```sql
DESCRIBE user_preferences;
```

### Select All Records
```sql
SELECT * FROM user_preferences;
```

### Count Records
```sql
SELECT COUNT(*) FROM user_preferences;
```

### Select a Specific User
```sql
SELECT * FROM user_preferences WHERE user_id = 'example_user_id';
```

### Add a New User
```sql
INSERT INTO user_preferences (user_id, api_key, voices, current_voice_id) 
VALUES ('example_user_id', 'example_api_key', '{"voice1": "id1", "voice2": "id2"}', 'id1');
```

### Update a User's API Key
```sql
UPDATE user_preferences 
SET api_key = 'new_api_key' 
WHERE user_id = 'example_user_id';
```

### Delete a User
```sql
DELETE FROM user_preferences 
WHERE user_id = 'example_user_id';
```
