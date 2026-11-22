# Arcadia

Arcadia es un mundo virtual multijugador que estoy construyendo en Rust. **Urano** es su motor 3D. En este adelanto puedes ver sus dos primeros escenarios y el arco que permite pasar de uno a otro.

<p align="center">
  <img src="../assets/arcadia-mundos.svg" width="800" alt="Vista isométrica animada de los dos escenarios de Urano. El primero tiene un monolito azul y un portal violeta. En el segundo, dos torres de colores flanquean una plataforma dorada y el portal es turquesa.">
</p>

La ilustración reproduce las posiciones y proporciones de las escenas del prototipo. El cristal turquesa del primer mundo está dibujado a partir de los vértices de `oasis_spire.glb`, uno de los modelos que puede cargar Urano.

En el cliente nativo puedes explorar a pie, saltar y alternar entre primera y tercera persona. Al cruzar el portal pasas al otro mundo. El servidor sincroniza los avatares a 60 Hz y el motor dibuja la escena con wgpu y shaders WGSL.

**Presentación próximamente.**

[Volver al perfil](../README.md)
