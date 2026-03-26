using UnityEngine;

public class DirectionalWeaponPrefab : MonoBehaviour
{
    private DirectionalWeapon weapon;
    private Rigidbody2D rb;
    private Vector3 direction;
    private float duration;

    void Start()
    {   
        weapon = GameObject.Find("Directional Weapon").GetComponent<DirectionalWeapon>();
        duration = weapon.stats[weapon.weaponLevel].duration;
        rb = GetComponent<Rigidbody2D>();

        direction = GetDirectionToClosestEnemy();
        float randomAngle = Random.Range(-0.15f, 0.15f);
        Vector2 rotated = new Vector2(
            direction.x * Mathf.Cos(randomAngle) - direction.y * Mathf.Sin(randomAngle),
            direction.x * Mathf.Sin(randomAngle) + direction.y * Mathf.Cos(randomAngle)
        );
        rb.linearVelocity = rotated * weapon.stats[weapon.weaponLevel].speed;

        AudioController.Instance.PlaySound(AudioController.Instance.directionalWeaponSpawn);
    }

    private Vector3 GetDirectionToClosestEnemy()
    {
        GameObject[] enemies = GameObject.FindGameObjectsWithTag("Enemy");
        float closestDist = float.MaxValue;
        Transform closest = null;

        foreach (GameObject enemy in enemies)
        {
            float dist = Vector3.Distance(transform.position, enemy.transform.position);
            if (dist < closestDist)
            {
                closestDist = dist;
                closest = enemy.transform;
            }
        }

        if (closest != null)
            return (closest.position - transform.position).normalized;

        return PlayerController.Instance.lastMoveDirection.normalized;
    }


    void Update()
    {
        duration -= Time.deltaTime;
        if (duration <= 0){
            transform.localScale = Vector3.MoveTowards(transform.localScale, Vector3.zero, Time.deltaTime * 5);
            if (transform.localScale.x == 0f){
                Destroy(gameObject);
            }
        }
    }

    private void OnCollisionEnter2D(Collision2D collision){
        if (collision.gameObject.CompareTag("Enemy")){
            Enemy enemy = collision.gameObject.GetComponent<Enemy>();
            enemy.TakeDamage(weapon.stats[weapon.weaponLevel].damage);
            AudioController.Instance.PlaySound(AudioController.Instance.directionalWeaponHit);
        }
    }
}
