plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "local.brainwaves.bridge"
    compileSdk = 35
    defaultConfig { applicationId = "local.brainwaves.bridge"; minSdk = 23; targetSdk = 28; versionCode = 1; versionName = "1.0" }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies { implementation("com.robotemi:sdk:1.138.0"); implementation("org.nanohttpd:nanohttpd:2.3.1") }
