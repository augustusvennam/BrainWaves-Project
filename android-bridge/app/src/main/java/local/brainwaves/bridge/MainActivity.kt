package local.brainwaves.bridge

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.*
import com.robotemi.sdk.Robot
import com.robotemi.sdk.TtsRequest
import com.robotemi.sdk.listeners.OnRobotReadyListener
import fi.iki.elonen.NanoHTTPD
import org.json.JSONObject
import java.util.UUID

/** Local LAN bridge. All SDK commands execute on Android's main thread. */
class MainActivity : Activity(), OnRobotReadyListener, Robot.TtsListener {
    private val robot = Robot.getInstance()
    private val main = Handler(Looper.getMainLooper())
    @Volatile private var ready = false
    @Volatile private var token = ""
    private lateinit var expression: TextView
    private var server: Bridge? = null
    private val commands = LinkedHashMap<String, JSONObject>()
    private val ttsCommands = HashMap<UUID, String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24, 24, 24, 24) }
        expression = TextView(this).apply { text = "BrainWaves — waiting for SDK"; textSize = 36f }
        val credential = EditText(this).apply { hint = "Enter bridge token (minimum 16 characters)"; inputType = 129 }
        val start = Button(this).apply { text = "Start bridge on port 8080" }
        start.setOnClickListener {
            if (credential.text.length < 16) { credential.error = "Use at least 16 characters"; return@setOnClickListener }
            token = credential.text.toString()
            server?.stop()
            server = Bridge().also { it.start(NanoHTTPD.SOCKET_READ_TIMEOUT, false) }
            start.text = "Bridge listening on LAN port 8080"
        }
        layout.addView(expression); layout.addView(credential); layout.addView(start)
        setContentView(layout)
        robot.addOnRobotReadyListener(this)
        robot.addTtsListener(this)
    }

    override fun onRobotReady(isReady: Boolean) {
        ready = isReady
        if (isReady) robot.onStart(packageManager.getActivityInfo(componentName, android.content.pm.PackageManager.GET_META_DATA))
        expression.text = if (isReady) "BrainWaves — connected" else "BrainWaves — disconnected"
        if (!isReady) synchronized(commands) { commands.values.filter { it.optString("status") == "accepted" }.forEach { it.put("status", "failed") } }
    }

    private fun update(id: String, status: String) {
        synchronized(commands) {
            commands[id]?.let { command ->
                if (command.optString("status") == "accepted") command.put("status", status)
            }
        }
    }

    override fun onTtsStatusChanged(ttsRequest: TtsRequest) {
        val id = ttsCommands[ttsRequest.id] ?: return
        val status = when (ttsRequest.status) {
            TtsRequest.Status.COMPLETED -> "completed"
            TtsRequest.Status.CANCELED -> "cancelled"
            TtsRequest.Status.ERROR, TtsRequest.Status.NOT_ALLOWED -> "failed"
            else -> return
        }
        update(id, status)
        ttsCommands.remove(ttsRequest.id)
    }

    private fun execute(id: String, action: String, payload: JSONObject) {
        if (synchronized(commands) { commands[id]?.optString("status") != "accepted" }) return
        if (!ready) { update(id, "failed"); return }
        try {
            when (action) {
                "speak" -> {
                    val request = TtsRequest.create(payload.getString("text"))
                    ttsCommands[request.id] = id
                    robot.speak(request)
                }
                "expression" -> {
                    expression.text = "Estimated state\n" + payload.getString("state")
                    update(id, "completed") // On-screen rendering, not physical movement.
                }
                "stop" -> {
                    robot.stopMovement()
                    robot.cancelAllTtsRequests()
                    synchronized(commands) { commands.values.filter { it.optString("id") != id && it.optString("status") == "accepted" }.forEach { it.put("status", "cancelled") } }
                    ttsCommands.clear()
                    // SDK invocation does not verify physical stopping.
                    update(id, "completed")
                }
            }
        } catch (_: Exception) { update(id, "failed") }
    }

    inner class Bridge : NanoHTTPD(8080) {
        private fun json(status: Response.Status, body: JSONObject): Response = newFixedLengthResponse(status, "application/json", body.toString())
        override fun serve(session: IHTTPSession): Response {
            if (token.isEmpty() || session.headers["authorization"] != "Bearer $token") return json(Response.Status.UNAUTHORIZED, JSONObject().put("error", "Unauthorized"))
            if (session.method == Method.GET && session.uri == "/api/status") return json(Response.Status.OK, JSONObject().put("robot_connected", ready).put("contract_version", 1))
            if (session.method == Method.GET && session.uri.startsWith("/api/commands/")) {
                val id = session.uri.substringAfterLast('/')
                return synchronized(commands) { commands[id]?.let { json(Response.Status.OK, it) } ?: json(Response.Status.NOT_FOUND, JSONObject().put("error", "Unknown command")) }
            }
            if (session.method != Method.POST || session.uri != "/api/commands") return json(Response.Status.NOT_FOUND, JSONObject())
            if (!ready) return json(Response.Status.SERVICE_UNAVAILABLE, JSONObject().put("error", "SDK disconnected"))
            val length = session.headers["content-length"]?.toIntOrNull() ?: 0
            if (length !in 1..4096) return json(Response.Status.BAD_REQUEST, JSONObject().put("error", "Invalid body size"))
            try {
                val body = HashMap<String, String>(); session.parseBody(body)
                val request = JSONObject(body["postData"] ?: "")
                val id = request.getString("id"); UUID.fromString(id)
                val action = request.getString("action"); val payload = request.getJSONObject("payload")
                if (action !in listOf("speak", "stop", "expression")) throw IllegalArgumentException()
                if (action == "speak" && (payload.getString("text").isBlank() || payload.getString("text").length > 300)) throw IllegalArgumentException()
                if (action == "expression" && payload.getString("state") !in listOf("Relaxed", "Engaged", "Excited", "Stressed")) throw IllegalArgumentException()
                synchronized(commands) {
                    commands[id]?.let { return json(Response.Status.OK, JSONObject().put("id", id).put("status", "accepted")) }
                    if (commands.values.count { it.optString("status") == "accepted" } >= 16) return json(Response.Status.SERVICE_UNAVAILABLE, JSONObject().put("error", "Command queue full"))
                    if (commands.size >= 100) commands.remove(commands.entries.first { it.value.optString("status") != "accepted" }.key)
                    commands[id] = JSONObject().put("id", id).put("status", "accepted").put("action", action)
                }
                main.post { execute(id, action, payload) }
                main.postDelayed({
                    val pending = synchronized(commands) { commands[id]?.optString("status") == "accepted" }
                    if (pending) {
                        update(id, "failed")
                        if (action == "speak") robot.cancelAllTtsRequests()
                        ttsCommands.entries.removeAll { it.value == id }
                    }
                }, 30000)
                return json(Response.Status.OK, JSONObject().put("id", id).put("status", "accepted"))
            } catch (_: Exception) { return json(Response.Status.BAD_REQUEST, JSONObject().put("error", "Invalid command")) }
        }
    }

    override fun onDestroy() {
        server?.stop()
        robot.removeOnRobotReadyListener(this); robot.removeTtsListener(this)
        main.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
