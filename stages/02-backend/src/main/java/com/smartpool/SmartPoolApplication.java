package com.smartpool;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class SmartPoolApplication {

    public static void main(String[] args) {
        SpringApplication.run(SmartPoolApplication.class, args);
    }
}
