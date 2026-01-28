"""
ModernGL 3D Video Renderer
Advanced 3D rendering using OpenGL for custom effects
"""

import moderngl
import numpy as np
from PIL import Image
import io
from pathlib import Path
from typing import List, Tuple
import math


class ModernGL3DRenderer:
    """
    Create 3D animated videos using ModernGL (free OpenGL wrapper)
    Perfect for custom particle effects, fluid simulations, and complex animations
    """
    
    def __init__(self, width: int = 1080, height: int = 1920):
        """Initialize with portrait dimensions for shorts"""
        self.width = width
        self.height = height
        self.ctx = moderngl.create_standalone_context()
        
        # Create framebuffer
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((width, height), 4)]
        )
        
    def create_particle_system_video(
        self, 
        text: str, 
        duration_frames: int = 120,
        particle_count: int = 1000
    ) -> List[Image.Image]:
        """
        Create particle system animation
        
        Args:
            text: Text to display
            duration_frames: Number of frames
            particle_count: Number of particles
            
        Returns:
            List of PIL Images
        """
        vertex_shader = '''
        #version 330
        
        in vec3 in_position;
        in vec3 in_color;
        in float in_size;
        
        out vec3 v_color;
        
        uniform mat4 mvp;
        uniform float time;
        
        void main() {
            vec3 pos = in_position;
            
            // Animate particles
            pos.x += sin(time + in_position.y * 2.0) * 0.1;
            pos.y += cos(time + in_position.x * 2.0) * 0.1;
            pos.z += sin(time * 0.5 + in_position.z) * 0.05;
            
            gl_Position = mvp * vec4(pos, 1.0);
            gl_PointSize = in_size * (1.0 + sin(time) * 0.3);
            v_color = in_color;
        }
        '''
        
        fragment_shader = '''
        #version 330
        
        in vec3 v_color;
        out vec4 fragColor;
        
        void main() {
            vec2 coord = gl_PointCoord - vec2(0.5);
            float dist = length(coord);
            
            if (dist > 0.5) {
                discard;
            }
            
            float alpha = 1.0 - (dist * 2.0);
            fragColor = vec4(v_color, alpha * 0.8);
        }
        '''
        
        prog = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )
        
        # Generate particles
        particles = self._generate_particles(particle_count)
        vbo = self.ctx.buffer(particles.tobytes())
        
        vao = self.ctx.vertex_array(
            prog,
            [
                (vbo, '3f 3f 1f', 'in_position', 'in_color', 'in_size')
            ]
        )
        
        frames = []
        
        for frame in range(duration_frames):
            self.fbo.use()
            self.ctx.clear(0.0, 0.0, 0.0, 1.0)
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            
            # Update uniforms
            time = frame / 30.0  # Assuming 30 FPS
            mvp = self._get_mvp_matrix(time)
            
            prog['mvp'].write(mvp.tobytes())
            prog['time'].value = time
            
            # Render
            vao.render(moderngl.POINTS)
            
            # Read frame
            data = self.fbo.read(components=4)
            image = Image.frombytes('RGBA', (self.width, self.height), data)
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            
            # Add text overlay
            image = self._add_text_overlay(image, text)
            
            frames.append(image)
        
        return frames
    
    def create_3d_waves_video(
        self,
        text: str,
        duration_frames: int = 120
    ) -> List[Image.Image]:
        """Create animated 3D wave surface"""
        
        vertex_shader = '''
        #version 330
        
        in vec3 in_position;
        
        out vec3 v_position;
        out vec3 v_normal;
        
        uniform mat4 mvp;
        uniform float time;
        
        void main() {
            vec3 pos = in_position;
            
            // Create waves
            float wave1 = sin(pos.x * 2.0 + time) * 0.2;
            float wave2 = cos(pos.y * 2.0 + time * 0.7) * 0.2;
            pos.z = wave1 + wave2;
            
            // Calculate normal for lighting
            float dx = cos(pos.x * 2.0 + time) * 0.4;
            float dy = -sin(pos.y * 2.0 + time * 0.7) * 0.28;
            v_normal = normalize(vec3(-dx, -dy, 1.0));
            
            gl_Position = mvp * vec4(pos, 1.0);
            v_position = pos;
        }
        '''
        
        fragment_shader = '''
        #version 330
        
        in vec3 v_position;
        in vec3 v_normal;
        
        out vec4 fragColor;
        
        uniform float time;
        
        void main() {
            vec3 light_dir = normalize(vec3(1.0, 1.0, 2.0));
            float diffuse = max(dot(v_normal, light_dir), 0.0);
            
            // Gradient color based on height
            vec3 color1 = vec3(0.2, 0.6, 1.0);
            vec3 color2 = vec3(1.0, 0.3, 0.8);
            vec3 color = mix(color1, color2, (v_position.z + 0.4) / 0.8);
            
            vec3 final_color = color * (0.4 + diffuse * 0.6);
            fragColor = vec4(final_color, 1.0);
        }
        '''
        
        prog = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )
        
        # Generate grid mesh
        vertices, indices = self._generate_grid_mesh(50, 50)
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        
        vao = self.ctx.vertex_array(
            prog,
            [(vbo, '3f', 'in_position')],
            ibo
        )
        
        frames = []
        
        for frame in range(duration_frames):
            self.fbo.use()
            self.ctx.clear(0.1, 0.1, 0.15, 1.0)
            self.ctx.enable(moderngl.DEPTH_TEST)
            
            time = frame / 30.0
            mvp = self._get_mvp_matrix(time)
            
            prog['mvp'].write(mvp.tobytes())
            prog['time'].value = time
            
            vao.render(moderngl.TRIANGLES)
            
            data = self.fbo.read(components=4)
            image = Image.frombytes('RGBA', (self.width, self.height), data)
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            image = self._add_text_overlay(image, text)
            
            frames.append(image)
        
        return frames
    
    def _generate_particles(self, count: int) -> np.ndarray:
        """Generate particle data"""
        particles = np.zeros(count, dtype=[
            ('position', np.float32, 3),
            ('color', np.float32, 3),
            ('size', np.float32, 1)
        ])
        
        for i in range(count):
            # Random position in sphere
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.random.uniform(0, np.pi)
            r = np.random.uniform(0.5, 2.0)
            
            particles['position'][i] = [
                r * np.sin(phi) * np.cos(theta),
                r * np.sin(phi) * np.sin(theta),
                r * np.cos(phi)
            ]
            
            # Rainbow colors
            hue = i / count
            particles['color'][i] = self._hsv_to_rgb(hue, 0.8, 1.0)
            
            particles['size'][i] = np.random.uniform(10, 30)
        
        return particles.view(np.float32).reshape(-1, 7)
    
    def _generate_grid_mesh(self, rows: int, cols: int) -> Tuple[np.ndarray, np.ndarray]:
        """Generate grid mesh for surface"""
        vertices = []
        
        for i in range(rows):
            for j in range(cols):
                x = (j / (cols - 1) - 0.5) * 4
                y = (i / (rows - 1) - 0.5) * 4
                z = 0
                vertices.append([x, y, z])
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Generate indices
        indices = []
        for i in range(rows - 1):
            for j in range(cols - 1):
                top_left = i * cols + j
                top_right = top_left + 1
                bottom_left = (i + 1) * cols + j
                bottom_right = bottom_left + 1
                
                indices.extend([top_left, bottom_left, top_right])
                indices.extend([top_right, bottom_left, bottom_right])
        
        return vertices, np.array(indices, dtype=np.int32)
    
    def _get_mvp_matrix(self, time: float) -> np.ndarray:
        """Get Model-View-Projection matrix"""
        aspect = self.width / self.height
        
        # Projection
        fov = np.radians(45)
        near, far = 0.1, 100.0
        f = 1.0 / np.tan(fov / 2)
        
        projection = np.array([
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), -1],
            [0, 0, (2 * far * near) / (near - far), 0]
        ], dtype=np.float32)
        
        # View (rotating camera)
        angle = time * 0.3
        eye_x = np.sin(angle) * 5
        eye_z = np.cos(angle) * 5
        eye_y = 2
        
        view = self._look_at(
            np.array([eye_x, eye_y, eye_z]),
            np.array([0, 0, 0]),
            np.array([0, 1, 0])
        )
        
        return projection @ view
    
    def _look_at(self, eye, center, up):
        """Create look-at matrix"""
        f = center - eye
        f = f / np.linalg.norm(f)
        
        s = np.cross(f, up)
        s = s / np.linalg.norm(s)
        
        u = np.cross(s, f)
        
        result = np.eye(4, dtype=np.float32)
        result[0, :3] = s
        result[1, :3] = u
        result[2, :3] = -f
        result[:3, 3] = -np.array([np.dot(s, eye), np.dot(u, eye), np.dot(-f, eye)])
        
        return result
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB"""
        import colorsys
        return colorsys.hsv_to_rgb(h, s, v)
    
    def _add_text_overlay(self, image: Image.Image, text: str) -> Image.Image:
        """Add text overlay to image"""
        from PIL import ImageDraw, ImageFont
        
        draw = ImageDraw.Draw(image)
        
        # Try to use a nice font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        # Calculate text position (centered at top)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (self.width - text_width) // 2
        y = 100
        
        # Draw text with outline
        outline_range = 3
        for adj_x in range(-outline_range, outline_range + 1):
            for adj_y in range(-outline_range, outline_range + 1):
                draw.text((x + adj_x, y + adj_y), text, font=font, fill=(0, 0, 0, 200))
        
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        return image
    
    def save_frames_as_video(self, frames: List[Image.Image], output_path: str, fps: int = 30):
        """Save frames as video using moviepy"""
        from moviepy.editor import ImageSequenceClip
        import numpy as np
        
        # Convert PIL images to numpy arrays
        frame_arrays = [np.array(frame.convert('RGB')) for frame in frames]
        
        clip = ImageSequenceClip(frame_arrays, fps=fps)
        clip.write_videofile(output_path, codec='libx264', audio=False)


if __name__ == "__main__":
    # Example usage
    renderer = ModernGL3DRenderer()
    
    # Create particle system video
    print("Generating particle system...")
    frames = renderer.create_particle_system_video("Amazing 3D Effects!", duration_frames=90)
    renderer.save_frames_as_video(frames, "output/particles_3d.mp4")
    
    # Create wave surface video
    print("Generating wave surface...")
    frames = renderer.create_3d_waves_video("Flowing Waves", duration_frames=90)
    renderer.save_frames_as_video(frames, "output/waves_3d.mp4")
    
    print("Videos generated successfully!")
