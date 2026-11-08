# 多阶段构建：Maven 构建 -> JRE 运行
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /workspace

# 国内 Maven 镜像，避免构建期依赖外网
COPY settings.xml /root/.m2/settings.xml

COPY pom.xml .
RUN mvn -B -q dependency:go-offline || true

COPY src ./src
RUN mvn -B -q clean package -DskipTests

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

RUN addgroup -S app && adduser -S app -G app

COPY --from=build /workspace/target/*.jar app.jar
USER app

EXPOSE 8080
ENV JAVA_OPTS="-XX:MaxRAMPercentage=70 -Duser.timezone=Asia/Shanghai"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
